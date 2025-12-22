import json
import os
from datetime import datetime

class TemporaryDataHandler:
    def __init__(self, base_dir="data/temp"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
    
    def salvar_json_cru(self, codigo_imovel, dados_dict):
        """Salva o JSON interceptado em disco com timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{codigo_imovel}_{timestamp}.json"
        path = os.path.join(self.base_dir, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dados_dict, f, indent=4, ensure_ascii=False)
            
        print(f"💾 [DataManager] JSON bruto salvo em: {path}")
        return path 

    def carregar_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)