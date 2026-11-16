# CILMUMBAI

Plans and starter code for the Claude Impact Lab Mumbai hackathon (21 November 2026) on civic budget and accountability.

| Folder | What it is |
|---|---|
| [mumbai-civic-platform/](mumbai-civic-platform/) | **Start here.** The final recommendation, **Aamcha Hishob** (आमचा हिशोब): one knowledge graph of Mumbai's civic data with a search and intelligence layer, data catalogue, ontology and implementation plan. |
| [aamcha-hishob-specs/](aamcha-hishob-specs/) | **How to build it.** Spec-driven development plan: constitution, process, milestones, and thirteen full specifications with requirements, acceptance criteria and task cards. |
| [app/](app/) | **The implementation**, built spec by spec. SPEC-001 (document archive) is built and tested. |
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
