<a name="top"></a>
[![ORCASTATLLM](./images/OrcaStatLLM.png)](https://algonet.open-research.tech/)
[![language](https://img.shields.io/badge/language-python3-239120)](https://python.org)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-886FBF?logo=googlegemini&logoColor=fff)](#)
[![Free](https://img.shields.io/badge/free_for_non_commercial_use-brightgreen)](#-license)

⭐ Star us on GitHub

## Table of Contents

- [About](#about)
  - [What is OrcaStatLLM Researcher?](#orcastatllm-researcher)
  - [OrcaStatLLM Architecture](#orcastatllm-architecture)
  - [Information Retrieval Process](#retrieval-architecture)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup Guide](#setting-up)
- [Examples & Demos](#example-demos)
- [Contributing](#contributing)

<br/><br/>

# About

## OrcaStatLLM Researcher

OrcaStatLLM Researcher is a self-contained research system that employs a multi-agent architecture powered by large language model. It orchestrates information gathering from academic repositories, statistical databases, and web sources, and then applies natural language processing for content filtering, relevance ranking, and knowledge synthesis. The system follows a modular pipeline architecture with specialized components for academic paper analysis, statistical data extraction, and visualization generation. Operating either as a fully autonomous agent or interactive research aide, it produces semantically rich documents with proper citation management and data visualization, leading to significant productivity improvement in research workflows without compromising stringent academic rigor.

## OrcaStatLLM Architecture

```mermaid
graph TD
    A[User Input: Research Topic] --> B[Topic Analyzer]
    B --> C[Academic Researcher]
    B --> D[Statistics Researcher]
    B --> E[Subtopic Researcher]
    C --> F[Content Generator]
    D --> F
    E --> F
    F --> G[Document Assembly]
    G --> H[Final Research Paper]
    
    subgraph External Sources
        I[ArXiv Papers]
        J[DOI Repositories]
        K[Web Content]
        L[Statistical Databases]
    end
    
    I --> C
    J --> C
    K --> E

```
## Retrieval Architecture

The retrieval system operates through specialized modules that target different information sources:

```mermaid
graph TD
    A[Research Topic] --> B[Topic Analysis]
    B --> C[Query Generation]
    C --> D[Source-Specific Queries]
    
    D --> E[Academic Source Retrieval]
    D --> F[Web Content Retrieval]
    D --> G[Statistical Data Retrieval]
    
    E --> E1[ArXiv API]
    E --> E2[DOI Resolver]
    E --> E3[PDF Extraction]
    
    F --> F1[Web Scraper]
    F --> F2[Wikipedia API]
    F --> F3[News API]
    
    G --> G1[Statistics Databases]
    
    E1 --> H[Content Processor]
    E2 --> H
    E3 --> H
    F1 --> H
    F2 --> H
    F3 --> H
    G1 --> H
    
    H --> I[Knowledge Repository]
    I --> J[Research Generation]
```

# Installation
This guide will help you get up and running with OrcaStatLLM in minutes.

## Prerequisites

- Gemini API Key (Can be retrived from https://aistudio.google.com/)
- Google CSE API Key (https://console.cloud.google.com/apis/dashboard)
``` yaml
Step-1: Create a Custom Search Engine on https://cse.google.com
Step-2: Add Those on config.json

//
{
  "gemini_api_keys": ["key1", "optionalkey2"],
  "google_cse": [
    {"cse_api": "key1", "cseid": "cse1"},
    {"cse_api": "key2optional", "cseid": "cse2optional"}
  ]
}


//

```
- Dependency Fixer (Fixes and install's all Dependency)

```
chmod +x install-dep.sh
sudo ./install-dep.sh
```

- Playwright
```
$ sudo pip install playwright
$ playwright install chromium
```
- Pandoc (For PDF Generation)

```bash
$ sudo apt install Pandoc
```

## Setting Up

```
$ git clone https://github.com/AlgoNetLab/OrcaStatLLM-Researcher
$ cd OrcaStatLLM-Researcher
$ pip3 install -r requirements.txt
$ python3 run.py 
```

# Example Demos

## Generated Papers

<p>
  <a href="./examples/papers/Quantum_Computi_6110.pdf">
    <img src="./examples/img/msedge_HKUJlzUuOQ.png" width="300" height="400" style="margin: 15px;">
  </a> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="examples/papers/Development_and_7336.pdf">
    <img src="examples/img/msedge_ZyOBtlF08d.png" width="300" height="400" style="margin: 15px;">
  </a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="examples/papers/Windows_Vulnera_4616.pdf">
    <img src="examples/img/msedge_BBPfLhjt9o.png" width="300" height="400" style="margin: 15px;">
  </a>
  <br>
</p>

## Demo Video

  
[![Video Title](https://img.youtube.com/vi/5gfsbCN-eJ4/0.jpg)](https://www.youtube.com/watch?v=5gfsbCN-eJ4)


# Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes and commit them (`git commit -m 'Add new feature'`).
4. Push to your branch (`git push origin feature-branch`).
5. Open a Pull Request.

Thank you for your contributions!



    
