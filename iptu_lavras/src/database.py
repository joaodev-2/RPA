from sqlalchemy import LargeBinary, create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# --- MODELOS (TABELAS) ---

class Imovel(Base):
    __tablename__ = 'imoveis'
    
    id = Column(Integer, primary_key=True)
    codigo_reduzido = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="PENDENTE") 
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamento
    debitos = relationship("DebitoIPTU", back_populates="imovel", cascade="all, delete-orphan")

class DebitoIPTU(Base):
    __tablename__ = 'debitos_iptu'
    
    id = Column(Integer, primary_key=True)
    imovel_id = Column(Integer, ForeignKey('imoveis.id'))
    
    ano = Column(Integer)
    parcela = Column(Integer)
    valor = Column(Float)
    vencimento = Column(String(20))
    situacao = Column(String(50))
    boleto_pdf = Column(LargeBinary, nullable=True)
    
    imovel = relationship("Imovel", back_populates="debitos")

# --- GERENCIADOR ---

class DatabaseHandler:
    def __init__(self, connection_string):
        print(f"🔌 [Database] Conectando ao banco...")
        self.engine = create_engine(connection_string, echo=False)
        self.Session = sessionmaker(bind=self.engine)
    
    def init_db(self):
        """Cria as tabelas se não existirem"""
        Base.metadata.create_all(self.engine)
        print("✅ [Database] Tabelas verificadas com sucesso!")

    def get_session(self):
        return self.Session()