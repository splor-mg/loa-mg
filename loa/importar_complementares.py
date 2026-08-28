"""Importa os demonstrativos que não cabiam no importador original.

As transformações aqui são deliberadamente simples: usam os mesmos TSVs que
originam os PDFs e preservam todas as linhas. O objetivo é que os novos
quadros do painel sejam atualizados automaticamente quando o repositório
volumes-loa mudar.
"""
from pathlib import Path
import csv
from .importar import _texto, _numero, _percentual, preencher, gravar, ler_tsv, nivel_do_codigo, so_uo


def _pct(valor):
    return _percentual(valor)


def _codigo_nivel(codigo):
    return str(nivel_do_codigo(codigo))


def importar_complementares(v1: Path | None, v2: Path | None, v3: Path | None, destino: Path) -> dict[str, int]:
    r = {}
    if v1 and v1.exists():
        r.update(_v1(v1, destino))
    if v2 and v2.exists():
        r.update(_v2(v2, destino))
    if v3 and v3.exists():
        r.update(_v3(v3, destino))
    return r


def _v1(v, d):
    r={}
    specs={
      'T2_DCGF_DEMONSTRATIVO_RECEITA_CORRENTE_FISCAL.txt':('receita_corrente_fiscal.csv',['espec','valor']),
      'T6_DCGF_Demonstrativo_Evolucao_Receita_por_Categoria_Economica.txt':('evolucao_receita.csv',['RECEITA_COD','RECEITA_DESC','VL_2022','perc_2022','VL_2023','perc_2023','VL_2024','perc_2024','VL_2025','perc_2025','VL_2026','perc_2026']),
      'T8_DCGF_RECEITA_CORRENTE_LIQUIDA.txt':('receita_corrente_liquida.csv',['espec','VL_LOA_REC','ordem','nvl']),
      'T12_DCGF_Demonstrativo_Evolucao_Despesa_Categoria_Economica.txt':('evolucao_despesa.csv',['ordem','espec','VL_DESP_2024','perc_2024','VL_DESP_2025','perc_2025','VL_DESP_2026','perc_2026']),
      'T13_DCGF_Demonstrativo_Consolidado_Despesa.txt':('consolidado_despesa_categoria.csv',['ordem','espec','tesouro','outras','total']),
      'T16_DCGF_Demons_Aplicacao_Recursos_Manut_Desenv_Ensino.txt':('aplicacao_ensino.csv',['cod','nvl','espec','VL_LOA']),
      'T17_DCGF_Demonst_Aplicacao_Recursos_Progr_Saude_Investim.txt':('aplicacao_saude_programas.csv',['cod','espec','valor']),
      'T18_DCGF_Demonst_Aplicacao_Recursos_Acoes_Servicos_Publicos_Saude.txt':('aplicacao_asps.csv',['espec','nvl','VL_LOA','cod']),
      'T19_DCGF_Demonstrativo_Aplicacao_Recursos_Amparo_Fomento_Pesquisa.txt':('aplicacao_pesquisa.csv',['cod','espec','valor']),
      'T20A_DCGF_Demonstrativo_Partic_Percentual_Pessoal_RCL_LRF.txt':('pessoal_rcl_lrf.csv',['cod','espec','perc','valor']),
      'T23_DCGF_Demonstrativo_do_Servico_da_divida_publica.txt':('servico_divida.csv',['espec','principal','acessorio','total']),
      'T25_DCGF_Demonstrativo_Aplicacao_Recursos_FUNDEB.txt':('aplicacao_fundeb.csv',['cod','espec','valor']),
      'T25_DCGF_PT2_PESSOAL_MAGISTERIO_RELATIVO_RECEITA_FUNDEB.txt':('fundeb_pessoal_magisterio.csv',['cod','espec','valor']),
      'T26_DCGF_DEMONSTRATIVO_RECURSOS_APLICADOS_ACOES_PARA_CRIANCA_E_ADOLESCENTE.txt':('acoes_crianca_adolescente.csv',['UO_COD','FUNCIONAL','ACAO_DESC','VL_DESP','EXCLUSIVA']),
      'T27_DCGF_Demonst_Despesas_UGEPREVI.txt':('despesas_ugeprevi.csv',['tipo','espec','valor']),
      'T37_DCGF_DEMONSTRATIVOS_RECURSOS_APLICADOS_SEGURANCA_ALIMENTAR_NUTRICIONAL.txt':('seguranca_alimentar.csv',['FUNCIONAL','ACAO_DESC','VL_DESP']),
      'T38_DCGF_DEMONSTRATIVO_RECEITAS_DESPESAS_PREVIDENCIARIAS_RPPS.txt':('previdencia_rpps.csv',['espec','nvl','VL_LOA']),
      'T39_DCGF_DEMONSTRATIVO_DA_POLITICA_DE_ATENDIMENTO_A_MULHER_VITIMA_DE_VIOLENCIA_NO_ESTADO.txt':('politica_mulher_violencia.csv',['UO_COD','FUNCIONAL','ACAO_DESC','VL_DESP','EXCLUSIVA']),
    }
    for src,(out,cols) in specs.items():
        p=v/src
        if not p.exists(): continue
        rows=[]
        for x in ler_tsv(p):
            vals=[]
            for c in cols:
                val=x.get(c,'')
                if out=='fundeb_pessoal_magisterio.csv' and c=='valor' and '%' in str(val):
                    val=_pct(val)
                elif c.startswith(('VL_','valor','principal','acessorio','total','tesouro','outras')):
                    val=_numero(val)
                elif c.startswith('perc') or c=='perc':
                    val=_pct(val)
                else:
                    val=_texto(val)
                vals.append(val)
            # For hierarchy fields use source nvl when present.
            rows.append(vals)
        rename={
          'RECEITA_COD':'codigo','RECEITA_DESC':'especificacao','VL_2022':'valor_2022','VL_2023':'valor_2023','VL_2024':'valor_2024','VL_2025':'valor_2025','VL_2026':'valor_2026',
          'VL_DESP_2024':'valor_2024','VL_DESP_2025':'valor_2025','VL_DESP_2026':'valor_2026','VL_LOA_REC':'valor','VL_LOA':'valor','nvl':'nivel','espec':'especificacao','ordem':'ordem',
          'perc_2022':'percentual_2022','perc_2023':'percentual_2023','perc_2024':'percentual_2024','perc_2025':'percentual_2025','perc_2026':'percentual_2026','perc':'percentual',
          'tesouro':'tesouro','outras':'outras_fontes','UO_COD':'uo_codigo','FUNCIONAL':'funcional','ACAO_DESC':'acao','VL_DESP':'valor','EXCLUSIVA':'exclusiva','tipo':'tipo','cod':'codigo','principal':'principal','acessorio':'acessorio','total':'total'
        }
        headers=[rename.get(c,c) for c in cols]
        # Hierarchy where the source has nvl.
        if 'nivel' not in headers and out in {'receita_corrente_liquida.csv','aplicacao_ensino.csv','aplicacao_asps.csv','previdencia_rpps.csv'}:
            pass
        if out in {'aplicacao_fundeb.csv','fundeb_pessoal_magisterio.csv'}:
            rows=[row+[('1' if not row[0] else '2')] for row in rows]
            headers += ['nivel']
        if out=='despesas_ugeprevi.csv':
            mapa={'Poder':'1','UO':'2','Acao':'3','Subtotal':'2','Total':'1'}
            rows=[row+[mapa.get(row[0],'3')] for row in rows]
            headers += ['nivel']
        r[out]=gravar(d,out,headers,rows)

    # T3 completo: não confundir com o resumo que o projeto já tinha.
    p=v/'T3_DCGF_Demonstrativo_Receita_Despesa_Segundo_Categorias_Economicas.txt'
    if p.exists():
        rows=[]
        for x in ler_tsv(p):
            rows.append([_texto(x.get('ordem')), _texto(x.get('RECEITA_DESC')),_numero(x.get('vl_rec')),_numero(x.get('vl_rec_total')),
                         _texto(x.get('DESPESA_DESC')),_numero(x.get('vl_desp')),_numero(x.get('vl_desp_total'))])
        r['receita_despesa_categorias.csv']=gravar(d,'receita_despesa_categorias.csv',
          ['ordem','receita_especificacao','receita_parcela','receita_total','despesa_especificacao','despesa_parcela','despesa_total'],rows)

    # T9 e T14/T15 possuem classificação hierárquica.
    p=v/'T9_DEMONSTRATIVO_RECEITA_ORCAMENTARIA_CORRENTE_ORDINARIA.txt'
    if p.exists():
        rows=[]
        for x in ler_tsv(p):
            c=_texto(x.get('cod_texto')); desc=_texto(x.get('descricao'))
            if not desc: continue
            rows.append([c,_texto(x.get('COD_FONTE')),desc,_numero(x.get('valor_desdobramento')),_numero(x.get('valor_especie')),_numero(x.get('valor_categoria')),_codigo_nivel(c)])
        r['receita_orcamentaria_corrente_ordinaria.csv']=gravar(d,'receita_orcamentaria_corrente_ordinaria.csv',['codigo','fonte','descricao','desdobramento','especie','categoria','nivel'],rows)

    for src,out in [('T14_DEMONSTRATIVO_DESPESA_FUNCAO_SUBFUNCAO_PROGRAMA_CONFORME_VINCULO_COM_RECURSOS.txt','despesa_vinculo_recursos.csv'),('T15_PROGRAMA_TRABALHO_GOVERNO.txt','programa_trabalho_governo.csv')]:
        p=v/src
        if not p.exists(): continue
        rows=[]
        for x in ler_tsv(p):
            if src.startswith('T14'):
                cols=['funcao','subfuncao','programa','especificacao','ordinarios','vinculados','arrecadados','total']; nums=cols[4:]
            else:
                cols=['funcao','subfuncao','programa','especificacao','pessoal','juros','outras_correntes','investimentos','inversoes','amortizacao','reserva','total']; nums=cols[4:]
            vals=[_texto(x.get(c,'')) if c not in nums else _numero(x.get(c,'')) for c in cols]
            nivel=str(sum(bool(_texto(x.get(c,''))) for c in ['funcao','subfuncao','programa'])+1)
            rows.append(vals+[nivel])
        headers=cols+['nivel']; r[out]=gravar(d,out,headers,rows)

    # T28, quatro partes.
    parts=[
      ('T28_DCGF_PT1_Receita_prevista_e_realizada.txt','programas_uniao_receita_realizada.csv',['RECEITA_COD','RECEITA_DESC','previsto','efet_ajust','ANO','MES','FONTE_EXEC']),
      ('T28_DCGF_PT2_Despesa_prevista_e_realizada.txt','programas_uniao_despesa_realizada.csv',['ANO','UO_COD','UO_SIGLA','PROGRAMA_COD','PROGRAMA_DESC','VL_LOA_DESP','VL_DESP_REALIZ','MES','FONTE_EXEC']),
      ('T28_DCGF_PT3_Receita_prevista_LOA.txt','programas_uniao_receita_loa.csv',['RECEITA_COD','RECEITA_DESC','VL_LOA_REC','FONTE_EXEC']),
      ('T28_DCGF_PT4_Despesa_prevista_LOA.txt','programas_uniao_despesa_loa.csv',['UO_COD','PROGRAMA_COD','PROGRAMA_DESC','UO_SIGLA','VL_LOA_DESP','FONTE_EXEC']),
    ]
    ren={'RECEITA_COD':'codigo','RECEITA_DESC':'receita','VL_LOA_REC':'valor','UO_COD':'uo_codigo','UO_SIGLA':'uo_sigla','PROGRAMA_COD':'programa_codigo','PROGRAMA_DESC':'programa','VL_LOA_DESP':'valor','VL_DESP_REALIZ':'realizado','FONTE_EXEC':'fontes_exec','ANO':'ano','MES':'mes','previsto':'previsto','efet_ajust':'realizado'}
    for src,out,cols in parts:
        p=v/src
        if not p.exists(): continue
        rows=[]
        for x in ler_tsv(p):
            vals=[]
            for c in cols:
                val=x.get(c,'')
                if c in {'previsto','efet_ajust','VL_LOA_REC','VL_LOA_DESP','VL_DESP_REALIZ'}: val=_numero(val)
                else: val=_texto(val)
                vals.append(val)
            rows.append(vals)
        r[out]=gravar(d,out,[ren.get(c,c) for c in cols],rows)

    # T30 (Anexo III, mas os dados estão em volume1 no repositório).
    p=v/'T30_INVESTIMENTOS_SEGUNDO_FUNCOES.txt'
    if p.exists():
        rows=[]
        for x in ler_tsv(p): rows.append([_texto(x.get('especificacao')),_numero(x.get('valor')),_pct(x.get('porcent'))])
        r['investimentos_funcoes.csv']=gravar(d,'investimentos_funcoes.csv',['especificacao','valor','percentual'],rows)
    return r


def _v2(v,d):
    r={}
    p=v/'tabela3'/'4711.csv'
    if p.exists():
        registros=ler_tsv(p)
        headers=['poder','codigo_uo','quantidade','valor','unidade_orcamentaria','qtdePoder','valorPoder','uo_funfip','nome_orgao']
        rows=[]
        for x in registros:
            rows.append([_texto(x.get(c,'')) if c not in {'quantidade','valor','qtdePoder','valorPoder'} else _numero(x.get(c,'')) for c in headers])
        r['funfip_pessoal_inativo.csv']=gravar(d,'funfip_pessoal_inativo.csv',headers,rows)
    p=v/'tabela5'
    if p.exists():
        rows=[]
        for f in sorted(p.glob('*.txt')):
            for x in preencher(ler_tsv(f),['nome_uo','nome_orgao']):
                esp=_texto(x.get('especificacao'))
                nivel='1' if (esp.startswith(('1.','2.','3.','4.','5.','6.')) or esp.upper().startswith('SUBTOTAL')) else '2'
                rows.append([_texto(x.get('nome_uo')), _texto(x.get('nome_orgao')), esp,
                             _numero(x.get('ordinario')), _numero(x.get('vinculado')), _numero(x.get('total')),nivel,f.stem])
        r['demais_recursos_financeiros.csv']=gravar(d,'demais_recursos_financeiros.csv',['unidade_orcamentaria','orgao','especificacao','ordinario','vinculado','total','nivel','arquivo_uo'],rows)
    return r


def _v3(v,d):
    r={}
    p=v/'consolidado'/'T2_INVESTIMENTOS_EMPRESA_SEGUNDO_DETALHAMENTO.txt'
    if p.exists():
        rows=[]
        for x in ler_tsv(p): rows.append([_texto(x.get(c,'')) if c=='empresas' else _numero(x.get(c,'')) for c in ['empresas','imob','societaria','outras','amort','total']])
        r['investimentos_empresa_detalhamento.csv']=gravar(d,'investimentos_empresa_detalhamento.csv',['empresa','imobilizacoes','participacao_societaria','outras_aplicacoes','amortizacao','total'],rows)
    p=v/'consolidado'/'T3_INVESTIMENTOS_SEGUNDO_FUNCOES_SUB_PROGRAMAS_PROJETOS_ATIVIDADES.txt'
    if p.exists():
        rows=[]
        for x in ler_tsv(p):
            c=_texto(x.get('codigo'))
            rows.append([c,_texto(x.get('especificacao')),_numero(x.get('projeto')),_numero(x.get('atividade')),_numero(x.get('total')),_codigo_nivel(c)])
        r['investimentos_funcoes_programas.csv']=gravar(d,'investimentos_funcoes_programas.csv',['codigo','especificacao','projeto','atividade','total','nivel'],rows)
    p=v/'tabela3'
    if p.exists():
        rows=[]
        for f in sorted(p.glob('*')):
            try: registros=ler_tsv(f)
            except Exception: continue
            headers=ler_tsv(f)[0] if False else None
            # ler_tsv não expõe os nomes originais após normalização; usamos o
            # DictReader diretamente para capturar os títulos variáveis.
            texto=f.read_text(encoding='utf-8-sig',errors='replace'); sep=';' if texto.count(';')>texto.count('\t') else '\t'
            reader=csv.DictReader(texto.splitlines(),delimiter=sep); campos=reader.fieldnames or []
            if len(campos)<4: continue
            uo=_texto(campos[0]); org=_texto(campos[1]); fonte=campos[2]
            for x in reader:
                fonte_val=_texto(x.get(fonte,''))
                for c in campos[3:]:
                    val=_texto(x.get(c,''))
                    if not val: continue
                    rows.append([uo,org,fonte_val,_texto(c),_numero(val)])
        r['investimentos_recursos_aplicacao.csv']=gravar(d,'investimentos_recursos_aplicacao.csv',['unidade_orcamentaria','orgao','fonte_recurso','aplicacao','valor'],rows)
    p=v/'tabela4'
    if p.exists():
        rows=[]
        for f in sorted(p.glob('*.txt')):
            regs=preencher(ler_tsv(f),['orgao','uo'])
            for x in regs:
                esp=_texto(x.get('especificacao')); total=_numero(x.get('total')); valor=_numero(x.get('valor')); nivel=_texto(x.get('nivel')) or '1'
                if not esp: continue
                rows.append([esp,total,valor,nivel,so_uo(x.get('orgao')),so_uo(x.get('uo')),f.stem])
        r['investimentos_detalhamento_uo.csv']=gravar(d,'investimentos_detalhamento_uo.csv',['especificacao','total','valor','nivel','orgao','unidade_orcamentaria','arquivo_uo'],rows)
    return r
