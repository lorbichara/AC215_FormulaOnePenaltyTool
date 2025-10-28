# ac215_FormulaOnePenaltyTool

## Team Members
* Beatrice Chen
* Bhargav Kosaraju
* Lorraine Bichara Assad

## Group Name
Formula One Penalty Tool

## Project Organization

```
├── README.md
├── reports
│   └── Milestone1.pdf
│   └── Milestone3.pdf
└── src
    ├── datapipeline
    │   ├── README.md
    │   ├── Dockerfile
    │   ├── pyproject.toml
    │   ├── uv.lock
    │   ├── requirements.txt
    │   ├── __init__.py
    │   ├── main.py
    │   ├── scraper.py
    │   ├── converter.py
    │   ├── assets
    └── rag
        ├── README.md
        ├── Dockerfile
        ├── pyproject.toml
        ├── uv.lock
        ├── docker-shell.sh
        ├── docker-entrypoint.sh
        ├── docker-compose.yml        
        └── ac215_rag.py
        └── assets
```

## Project
This project aims to make Formula 1 penalties more transparent and understandable for fans. Governed by the FIA, F1 penalties often appear inconsistent due to the complexity of the Sporting and Technical Regulations. This application takes a given race penalty and provides an accessible explanation of the infringement, referencing the official FIA regulations. It also analyzes the fairness of the penalty by comparing it to historical cases, helping users better grasp how penalties are determined and whether they align with past precedents.

## Milestone 2
In this milestone, we have set up the core infrastrucutre of the project. This include setting up the environment, as well as a data collection pipeline and a RAG setup.

See Milestone 1 [here](reports/Milestone1.pdf).

## Milestone 3
See the Milestone 3 midterm presentation [here](reports/Milestone3.pdf).

For this milestone, we applied feedback received in Milestone 2 including:
- Removed data files from GitHub repository
- Add a dedicated folder for reports/documents (MS1 proposal, MS3 midterm presentation)
- Include repository structure in the main README

### Data
See [Data Pipeline README](src/datapipeline/README.md) for more details on the data pipeline.

### RAG
See [RAG README](src/rag/README.md) for more details on the RAG set up.
