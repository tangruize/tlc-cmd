------------------------------- MODULE DieHard_json -------------------------------
EXTENDS DieHard,
        TLC,
        TLCExt, \* Trace operator &
        Json    \* JsonSerialize operator (both in CommunityModules-deps.jar)

(*
  The trick is that TLC evaluates disjunct 'Export' iff 'RealInv' equals FALSE.
  JsonInv is the invariant that we have TLC check, i.e. appears in the config.
*)
JsonInv ==
    \/ RealInv:: big /= 4 \* The ordinary invariant to check in EWD840 module.
    \/ Export:: /\ JsonSerialize("trace.json", Trace)
                /\ FALSE \*TLCSet("exit", FALSE) \* Stop model-checking *with* TLC reporting
                                        \* the usual text-based error trace. Replace
                                        \* with TRUE to not to print the error-trace
                                        \* and terminate with zero process exit
                                        \* value.

(* 3.
  Grab recent tla2tools.jar and CommunityModules-deps.jar (or Toolbox):
   wget -q https://nightly.tlapl.us/dist/tla2tools.jar \
           https://modules.tlapl.us/releases/latest/download/CommunityModules-deps.jar
*)

=============================================================================