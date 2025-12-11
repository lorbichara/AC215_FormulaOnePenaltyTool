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
    └── api
        ├── README.md
        ├── main.py
└── tests
    └── integration
        ├── test_api.py
    └── system
        ├── test_system_api.py
    └── unit
        ├── test_unit.py
```

---

## Project
This project aims to make Formula 1 penalties more transparent and understandable for fans. Governed by the FIA, F1 penalties often appear inconsistent due to the complexity of the Sporting and Technical Regulations. This application takes a given race penalty and provides an accessible explanation of the infringement, referencing the official FIA regulations. It also analyzes the fairness of the penalty by comparing it to historical cases, helping users better grasp how penalties are determined and whether they align with past precedents.

## Milestone 1
See Milestone 1 [here](reports/Milestone1.pdf).


## Milestone 2
In this milestone, we have set up the core infrastrucutre of the project. This include setting up the environment, as well as a data collection pipeline and a RAG setup.

### Data
[Data Pipeline README](src/datapipeline/README.md)

### RAG
[RAG README](src/rag/README.md)


## Milestone 3
See the Milestone 3 midterm presentation [here](reports/Milestone3.pdf).

For this milestone, we applied feedback received in Milestone 2 including:
- Removed data files from GitHub repository
- Add a dedicated folder for reports/documents (MS1 proposal, MS3 midterm presentation)
- Include repository structure in the main README
- Updated the UI mock up, see [here](https://twine-claw-08738571.figma.site)

## Milestone 4
### Application Design
[Application design doc](reports/Milestone4-ApplicationDesignDocument.pdf)

### Data Versioning
[Data Versioning README](src/datapipeline/DATAVERSIONING_README.md)

### Frontend
[Frontend README](src/frontend/frontend-template/README.md)

### API
[API README](src/api/README.md)

#### Model Fine-Tuning
[Fine-Tuning README](src/finetune/README.md)


### CI and Testing
[Testing README](tests/README.md)


## Milestone 5
### Deployment
[Deployment README](src/deployment/README.md)

### Blog
Coming Soon!

### Video
Coming Soon!
