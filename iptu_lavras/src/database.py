from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Imovel(Base):
    __tablename__ = 'imoveis'
    id = Column(Integer, primary_key=True)
    codigo_reduzido = Column(String(50), unique=True, nullable=False)
    status = Column(String(50), default="PENDENTE") 
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    dados_brutos = Column(JSONB, nullable=True) 
    debitos = relationship("DebitoIPTU", back_populates="imovel", cascade="all, delete-orphan")

class DebitoIPTU(Base):
    __tablename__ = 'debitos_iptu'
    
    id = Column(Integer, primary_key=True)
    imovel_id = Column(Integer, ForeignKey('imoveis.id'))
    
    ano = Column(Integer, nullable=False)
    parcela = Column(Integer)
    valor = Column(Float)
    
    # Novas colunas de data
    vencimento = Column(String(20))          
    vencimento_original = Column(String(20)) 
    
    situacao = Column(String(50)) # "Aberto", "Quitado", "Cancelado"
    boleto_pdf = Column(LargeBinary, nullable=True) # Será NULL se estiver quitado
    
    imovel = relationship("Imovel", back_populates="debitos")

class DatabaseHandler:
    # ... (O restante da classe permanece igual) ...
    def __init__(self, connection_string):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        self.engine = create_engine(connection_string, echo=False)
        self.Session = sessionmaker(bind=self.engine)
    
    def init_db(self):
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.Session()