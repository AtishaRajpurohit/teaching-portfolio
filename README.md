# Teaching Portfolio

Live site: **https://atisharajpurohit.github.io/teaching-portfolio/**

I teach to learn. I learn to teach.

One semester as an assistant lecturer for the Sunday AI Agents bootcamp at SupportVectors AI Labs, teaching a 50 to 60 person weekly cohort. This repo holds the interactive artifacts I built for those lectures, the labs I own, and the site that ties them together.

## What is here

```
index.html          The front page
everything.html     The full archive: every lecture, artifact, lab, talk, and article
artifacts/          Six interactive lecture artifacts plus the MCP attack surface explorer
labs/               Two runnable labs
assets/             Preview videos and images
resume.pdf          Resume
```

## The artifacts

Each lecture shipped with a self-contained interactive HTML artifact, built weekly with Claude Code and Claude Design as part of my prep pipeline. Open them straight from the site, or from `artifacts/`.

| Lecture | Artifact | Source taught |
|---|---|---|
| 1 | Evolution of Prompts and Context Engineering | [The Decreasing Value of Chain of Thought](https://gail.wharton.upenn.edu/research-and-insights/tech-report-chain-of-thought/) |
| 2 | MCP Threat Matrix + Attack Surface explorer | [MCP: Landscape, Security Threats (arXiv)](https://arxiv.org/abs/2503.23278) |
| 3 | Agentic Context Engineering | [ACE (arXiv)](https://arxiv.org/abs/2510.04618) |
| 4 | Mem0 | [Mem0 (arXiv)](https://arxiv.org/abs/2504.19413) |
| 5 | Harness Evolution | Anthropic engineering: [harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps), [effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) |
| 6 | Agentic Systems, a case study into Openclaw | |

The decks teach published papers and articles, credited above and inside each artifact.

## The labs

**RAG Faithfulness Checker** (`labs/rag-faithfulness-checker/`): demonstrating hallucinations by LLMs and the robustness of your prompts, with promptfoo.

```bash
cd labs/rag-faithfulness-checker
npx promptfoo eval
```

**Agentic Context Engineering Lab** (`labs/agentic-context-engineering/`): the context playbook built from scratch, showing the generate, reflect, curate loop.

```bash
cd labs/agentic-context-engineering
uv sync
python demo.py
```

Additional labs were co-created with SupportVectors AI Labs and are available on request considering copyright. Session recordings available on request.

## Contact

atisha.rajpurohit@gmail.com · [LinkedIn](https://www.linkedin.com/in/atisha-rajpurohit) · [Medium](https://medium.com/@AtishaRajpurohit)
