import sys
sys.path.insert(0, '.')
import os
os.environ['KILICHAT_DISABLE_EMBEDDINGS'] = '1'

from chat import mesaj_isle
from brain import Brain
from tools import TOOLS

brain = Brain()
try:
    result = mesaj_isle('merhaba nasilsin', brain, "Sen Başak'sın — Casper'ın kişisel asistanısın.", lambda code: None, TOOLS)
    print('Result:', result)
except Exception as e:
    print('Error:', type(e).__name__, str(e)[:300])