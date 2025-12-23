from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()

class Imovel(Base):
    __tablename__ = 'imoveis'
    
    id = Column(Integer, primary_key=True)
    codigo_reduzido = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="PENDENTE") 
    data_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Campo para auditoria/histórico (Salva o retorno completo do Scraper)
    dados_brutos = Column(JSONB, nullable=True) 
    
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
    
    # Campo binário para armazenar o arquivo PDF dentro do banco
    boleto_pdf = Column(LargeBinary, nullable=True) 
    
    imovel = relationship("Imovel", back_populates="debitos")

class DatabaseHandler:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string, echo=False)
        self.Session = sessionmaker(bind=self.engine)
    
    def init_db(self):
        """Cria as tabelas caso não existam."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.Session()