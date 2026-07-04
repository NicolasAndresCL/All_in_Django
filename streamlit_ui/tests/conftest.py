"""
conftest de los tests de la UI Streamlit.

Inserta `streamlit_ui/` en sys.path para poder importar `api_client` igual que
lo hace Streamlit al ejecutar `streamlit run app.py` (que añade la carpeta del
script al path). Así los tests no dependen de instalar la UI como paquete.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
