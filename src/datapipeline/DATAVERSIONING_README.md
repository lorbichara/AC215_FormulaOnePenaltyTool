# Data Versioning with DVC

This documentation explains how Data Version Control (DVC) is used to manage and version the F1 decision documents that are stored in the `input` folder.

DVC provides the abilitiy to treat large files and datasets just like code, ensuring reproducibility and tracking changes over time without committing large binaries directly to Git.

#### Versioned Data

The following directory is under DVC management:

| Folder | Contents | Versioning File |
| :--- | :--- | :--- |
| `input/` | F1 Decision PDF documents downloaded from a GCP bucket. | `./input.dvc` |

#### How DVC Works in This Project

Since the `input` folder is versioned, every time a PDF document is added, or deleted in that folder, DVC tracks the change by updating a small metadata file: `input.dvc`.

##### 1. The `input.dvc` File

The actual large PDF files are **not** stored in the Git repository. Instead, the `input.dvc` file is created and committed to Git.
This file contains:
* **A pointer** to the location (in this case, the GCP Bucket **f1penaltydocs**) where the actual data files are stored, as defined by the DVC remote configuration.
* A **hash value (checksum)** of the data currently in `input/`. This checksum acts as the unique identifier for that specific version of the dataset.

##### 2. Workflow Summary
Steps to be followed to updated the version of F1 decision documents:

| Step | Command | Description |
| :--- | :--- | :--- |
| **Track Changes** | `dvc add input` | This calculates the new hash, moves the actual data to the DVC cache, and updates the `input.dvc` file. |
| **Commit Metadata** | `git commit -m <commit message>` | This commits the **small** `input.dvc` file to the Git history, linking the Git commit to a specific data version. |
| **Store Data** | `dvc push` | This uploads the actual versioned data (the PDF files) from the local DVC cache to the defined **DVC remote storage** (which should be configured to point to the remote GCP bucket). |
| **Update Git** | `git push origin main <label>

##### 3. Reproducibility (Checking Out Data)

To switch back to a previous version of the F1 documents, just simply use standard Git commands followed by DVC's retrieval command:

1.  **Change Git Commit:** `git checkout <commit_hash_of_past_version>`
2.  **Retrieve Data:** `dvc checkout`

The `dvc checkout` command reads the `input.dvc` file associated with that Git commit and downloads the exact corresponding dataset from the remote storage into the `input` folder, ensuring that the system runs against the correct historical data.

This process ensures that anyone checking out a specific Git commit will automatically get the exact version of the F1 decision documents used at that time, making  the entire RAG pipeline fully reproducible.
