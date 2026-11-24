"""The Studio: turns a production brief into moves on outside tools (Splice, Suno, Epidemic Sound, Spotify).

The brains (`taste/`) hold what each person likes and decide nothing except through their APPROVED.md. The engine
(`trackcard.engine`) collects bounces and drops, measures them and writes one brief per project. The Studio sits after
the engine: it proposes tool moves for a brief, compares outside measurements with trackcard's, and keeps a ledger of
what a person picked, so the next bounce's diff can say which pick closed which gap.

Everything here is a pure function of files in the repository and inputs a session passes in. The connectors themselves
live in Claude sessions (engine/STUDIO.md is the playbook); nothing here calls the network, spends a credit, uploads or
downloads. Tools propose, people choose, and one brain's rules never steer the other person's move.
"""
