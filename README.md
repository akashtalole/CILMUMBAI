# CILMUMBAI

Plans and starter code for the Claude Impact Lab Mumbai hackathon (21 November 2026) on civic budget and accountability.

> **Impact Lab demo: [Follow the Rupee](https://akashtalole.github.io/CILMUMBAI/rupee/)**. Open a ward and see where its
> monsoon road money went, which bills are in question and why (each linked to its dataset row), fair grades for the
> ward and every contractor, the next fixes ranked by risk within the remaining budget, and what happened to any
> complaint, in Marathi, Hindi or English. Built on the challenge's synthetic dataset; see
> [SPEC-040](aamcha-hishob-specs/specs/SPEC-040-follow-the-rupee.md) and `app/datasets/follow-the-rupee/results/`.

| Folder | What it is |
|---|---|
| [mumbai-civic-platform/](mumbai-civic-platform/) | **Start here.** The final recommendation, **Aamcha Hishob** (आमचा हिशोब): one knowledge graph of Mumbai's civic data with a search and intelligence layer, data catalogue, ontology and implementation plan. |
| [aamcha-hishob-specs/](aamcha-hishob-specs/) | **How to build it.** Spec-driven development plan: constitution, process, milestones, and thirteen full specifications with requirements, acceptance criteria and task cards. |
| [app/](app/) | **The implementation**, built spec by spec. SPEC-001 to SPEC-009 and SPEC-011 are built and tested: the intake desk has read real documents end to end, real BMC ward boundaries load into the place spine, the graph answers "where did the money for this road go" with sources and gaps, SPEC-007 puts it all behind one API with access tiers and a citation check, the citizen desk (SPEC-008) answers residents in Marathi, Hindi or English from it, the workflow engine (SPEC-009) runs the pipeline with review gates that only a reviewer can pass, and the audit desk (SPEC-011) writes challenged, sourced ward findings that code checks before a reviewer releases them. |
| [mumbai-civic-graph/](mumbai-civic-graph/) | The first slice in detail: five idea plans, tender portal reference, the multi-agent system, and working starter code (agent definitions, session client, LangGraph pipeline). |
| [mumbai-civic-ideas/](mumbai-civic-ideas/) | Forty-one ideas rated for value and feasibility, including a full plan for the BMC and SRA redevelopment dispute. |

Status: design documents, plus starter code that has been syntax-checked and dry-run but not run against the Claude API or a real database.

## Documentation site

The same documents are published as a website with MkDocs (Material theme) at <https://akashtalole.github.io/CILMUMBAI/>.

```sh
pip install -r requirements-docs.txt
mkdocs serve            # preview at http://127.0.0.1:8000
```

`docs/` holds symlinks to the folders above, so files stay where they are. A GitHub Actions workflow builds the site in strict mode on pull requests and, on every push to `main`, publishes it to the `gh-pages` branch. To turn the site on once: **Settings → Pages → Build and deployment → Deploy from a branch → `gh-pages` / root**.
