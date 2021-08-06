------------------------------ MODULE TPaxos --------------------------------
(*
Specification of the consensus protocol in PaxosStore.

See [PaxosStore@VLDB2017](https://www.vldb.org/pvldb/vol10/p1730-lin.pdf)
by Tencent.

TPaxos is an variant of Basic Paxos, every server maintain a two-dimension
array contained the real state of itself and the view state from itself to
other servers. Both the real state and the view state is the triple like
Basic Paxos <<m, n, v>>, m is the maximum ballot number that acceptor promised,
<<n, v>> is the latest proposal that acceptor accepted. The algorithm reaches
consensus by meaning of updating the real state and the view state continually.
*)
EXTENDS Integers, FiniteSets
-----------------------------------------------------------------------------
CONSTANTS
    Participant,  \* the set of partipants
    Value         \* the set of possible input values for Participant to propose

None == CHOOSE b : b \notin Value \* an unspecified value that is not in Value
NP == Cardinality(Participant) \* number of p \in Participants

\* We generate the quorum system instead of input manually
Quorum == {Q \in SUBSET Participant : Cardinality(Q) * 2 >= NP + 1}
ASSUME QuorumAssumption ==
    /\ \A Q \in Quorum : Q \subseteq Participant
    /\ \A Q1, Q2 \in Quorum : Q1 \cap Q2 # {}

Ballot == Nat

(*
To make ballot total order, we let different participant use different ballot
numbers.
*)
Max(m, n) == IF m > n THEN m ELSE n
Injective(f) == \A a, b \in DOMAIN f: (a # b) => (f[a] # f[b])
PIndex == CHOOSE f \in [Participant -> 1 .. NP] : Injective(f)
Bals(p) == {b \in Ballot : b % NP = PIndex[p] - 1} \* allocate ballots for each p \in Participant
-----------------------------------------------------------------------------
\* state in the two-dimension array
State == [maxBal: Ballot \cup {-1},
         maxVBal: Ballot \cup {-1}, maxVVal: Value \cup {None}]

InitState == [maxBal |-> -1, maxVBal |-> -1, maxVVal |-> None]
(*
For simplicity, in this specification, we choose to send the complete state
of a participant each time. When receiving such a message, the participant
processes only the "partial" state it needs.
*)
Message == [from: Participant, to : SUBSET Participant, state: [Participant -> State]]
-----------------------------------------------------------------------------
VARIABLES
    state,  \* state[p][q]: the state of q \in Participant from the view of p \in Participant
    msgs    \* the set of messages that have been sent

vars == <<state, msgs>>

TypeOK ==
    /\ state \in [Participant -> [Participant -> State]]
    /\ msgs \subseteq Message

Send(m) == msgs' = msgs \cup {m}
-----------------------------------------------------------------------------
Init ==
    /\ state = [p \in Participant |-> [q \in Participant |-> InitState]]
    /\ msgs = {}
(*
p \in Participant starts the prepare phase by issuing a ballot b \in Ballot.
The participant p will update its real state which means p accept the prepare(b)
request. We send the complete state for simplicity and the receiver will processes
only the "partial" state it needs.

The participant p can not send message to itself to decrease the states while
model checking.
*)
Prepare(p, b) ==
    /\ b \in Bals(p)
    /\ state[p][p].maxBal < b
    /\ state' = [state EXCEPT ![p][p].maxBal = b]
    /\ Send([from |-> p, to |-> Participant, state |-> state'[p]])
(*
q \in Participant updates its own state state[q] according to the actual state
pp of p \in Participant extracted from a message m \in Message it receives.
This is called by OnMessage(q).

Sometimes the method of updating real state will bring some different execution
, e.g., when receiving <<3, 2, v1>> and its current state is <<1, -1, none>>,
the message can be regard as combination of prepare(3) requestand accept(2, v1)
request, and the participant can update to <<3, -1, none>> or <<3, 2, v1>>.
Here the participant will update to <<3, -1, none>>.

Note: pp is m.state[p]; it may not be equal to state[p][p] at the time
UpdateState is called.
*)
UpdateState(q, p, pp) ==
    LET maxB == Max(state[q][q].maxBal, pp.maxBal)
    IN  state' = [state EXCEPT
                  ![q][p].maxBal = Max(@, pp.maxBal),\* make promise
                  ![q][p].maxVBal = Max(@, pp.maxVBal),
                  ![q][p].maxVVal = IF state[q][p].maxVBal < pp.maxVBal
                                    THEN pp.maxVVal ELSE @,
                  ![q][q].maxBal = maxB, \* make promise first and then accept
                  ![q][q].maxVBal = IF maxB <= pp.maxVBal  \* accept
                                    THEN pp.maxVBal ELSE @,
                  ![q][q].maxVVal = IF maxB <= pp.maxVBal  \* accept
                                    THEN pp.maxVVal ELSE @]
(*
q \in Participant receives and processes a message in Message.
To
*)
OnMessage(q) ==
    \E m \in msgs :
        /\ q \in m.to
        /\ LET p == m.from
           IN  UpdateState(q, p, m.state[p])
        /\ LET qm == [from |-> m.from, to |-> m.to \ {q}, state |-> m.state] \*remove q from to
               nm == [from |-> q, to |-> {m.from}, state |-> state'[q]] \*new message to reply
           IN  IF \/ m.state[q].maxBal < state'[q][q].maxBal
                  \/ m.state[q].maxVBal < state'[q][q].maxVBal
               THEN msgs' = (msgs \ {m}) \cup {qm, nm}
               ELSE msgs' = (msgs \ {m}) \cup {qm}
(*
p \in Participant starts the accept phase by issuing the ballot b \in Ballot
with value v \in Value.

The participant p can not send message to itself to decrease the states while
model checking.
*)
Accept(p, b, v) ==
    /\ b \in Bals(p)
    /\ state[p][p].maxBal <= b \*corresponding the first conjunction in Voting
    /\ state[p][p].maxVBal # b \* correspongding the second conjunction in Voting
    /\ \E Q \in Quorum :
       /\ \A q \in Q : state[p][q].maxBal = b
       \* pick the value from the quorum
       (*/\ \/ \A q \in Q : state[p][q].maxVBal = -1 \* free to pick its own value
          \/ \E q \in Q : \* v is the value with the highest maxVBal in the quorum
                /\ state[p][q].maxVVal = v
                /\ \A r \in Q : state[p][q].maxVBal >= state[p][r].maxVBal
        *)
    \*choose the value from all the local state
    /\ \/ \A q \in Participant : state[p][q].maxVBal = -1 \* free to pick its own value
       \/ \E q \in Participant : \* v is the value with the highest maxVBal
            /\ state[p][q].maxVVal = v
            /\ \A r \in Participant: state[p][q].maxVBal >= state[p][r].maxVBal
    /\ state' = [state EXCEPT ![p][p].maxVBal = b,
                              ![p][p].maxVVal = v]
    /\ Send([from |-> p, to |-> Participant, state |-> state'[p]])
---------------------------------------------------------------------------
Next == \E p \in Participant : \/ OnMessage(p)
                               \/ \E b \in Ballot : \/ Prepare(p, b)
                                                    \/ \E v \in Value : Accept(p, b, v)
Spec == Init /\ [][Next]_vars
---------------------------------------------------------------------------
ChosenP(p) == \* the set of values chosen by p \in Participant
    {v \in Value : \E b \in Ballot :
                       \E Q \in Quorum: \A q \in Q: /\ state[p][q].maxVBal = b
                                                    /\ state[p][q].maxVVal = v}

chosen == UNION {ChosenP(p) : p \in Participant}

Consistency == Cardinality(chosen) <= 1

THEOREM Spec => []Consistency
=============================================================================
\* Modification History
\* Last modified Mon Sep 09 15:59:38 CST 2019 by stary
\* Created Mon Sep 02 15:47:52 GMT+08:00 2018 by stary