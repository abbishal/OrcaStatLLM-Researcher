# Common Errors

## ModuleNotFoundError: No module named 'exceptions'

### Error Message
```
Traceback (most recent call last):
  File "/home/kali/Desktop/OrcaStatLLM-Researcher/run.py", line 2, in <module>
    from app import app
  File "/home/kali/Desktop/OrcaStatLLM-Researcher/app.py", line 14, in <module>
    from modules.researcher import OrcaStatLLMScientist
  File "/home/kali/Desktop/OrcaStatLLM-Researcher/modules/researcher.py", line 21, in <module>
    from modules.document.markdown_generator import MarkdownGenerator
  File "/home/kali/Desktop/OrcaStatLLM-Researcher/modules/document/markdown_generator.py", line 11, in <module>
    from modules.document.pdf_converter import PDFConverter
  File "/home/kali/Desktop/OrcaStatLLM-Researcher/modules/document/pdf_converter.py", line 10, in <module>
    from docx import Document
  File "/usr/local/lib/python3.11/dist-packages/docx.py", line 30, in <module>
    from exceptions import PendingDeprecationWarning
ModuleNotFoundError: No module named 'exceptions'
```

### Fix

```
pip install --upgrade python-docx
```

## Dependency Error in weasyprint

```
sudo pip install weasyprint
```
