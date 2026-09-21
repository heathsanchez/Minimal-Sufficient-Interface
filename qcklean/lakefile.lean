import Lake
open Lake DSL

package qck where
  moreLeanArgs := #["-DautoImplicit=false"]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @
  "44ba35c6daa9d69aff8fed9fff9bbde17ded774d"

@[default_target]
lean_lib QCK where
  srcDir := "."
  roots := #[`QCKCore, `QCKCoreTest, `QCKFiniteLinear, `QCKFiniteLinearTest, `QCKAPI, `QCKAPITest, `QCKAxiomAudit,
    `CLC.Verdict, `CLC.VerdictTest,
    `CLC.Transport, `CLC.TransportTest,
    `CLC.Continuation, `CLC.ContinuationTest,
    `CLC.Support, `CLC.SupportTest,
    `CLC.Hypergraph, `CLC.HypergraphTest,
    `CLC.Query, `CLC.QueryTest,
    `CLC.Quotient, `CLC.QuotientTest,
    `CLC.Flash, `CLC.FlashTest,
    `CLC.Grow, `CLC.GrowTest,
    `CLC.Fixtures, `CLC.Audit]
