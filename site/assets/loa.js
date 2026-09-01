/* ---------------------------------------------------------------
   Interatividade das tabelas: filtro, ordenação, hierarquia
   expansível e exportação para CSV.

   Este é o ÚNICO arquivo JavaScript do projeto e ele é genérico:
   funciona para qualquer tabela gerada pelo Python. A equipe não
   precisa mexer aqui para publicar demonstrativos novos.

   REGRA CENTRAL — visibilidade de linha
   -------------------------------------
   Duas coisas independentes podem esconder uma linha:

     data-recolhida      → está dentro de um ramo fechado da árvore
     data-oculta-filtro  → não casou com o texto digitado no filtro

   Nenhuma das duas mexe no atributo `hidden` diretamente. O `hidden`
   é sempre RECALCULADO a partir das duas por `aplicarVisibilidade()`.

   Na versão anterior, filtro e hierarquia escreviam ambos em `hidden`
   e se apagavam mutuamente: filtrar apagava o estado da árvore e, ao
   limpar o filtro, a tabela ficava num estado que não era nem
   expandido nem recolhido — só as linhas do último filtro
   continuavam visíveis.
   --------------------------------------------------------------- */

(function () {
  "use strict";

  function texto(celula) {
    return (celula.textContent || "").trim();
  }

  function numero(celula) {
    var bruto = celula.getAttribute("data-valor");
    return bruto === null ? NaN : parseFloat(bruto);
  }

  /* -------------------------------------------------- visibilidade */

  function aplicarVisibilidade(linha) {
    var esconder =
      linha.hasAttribute("data-recolhida") ||
      linha.hasAttribute("data-oculta-filtro");
    if (esconder) {
      linha.setAttribute("hidden", "");
    } else {
      linha.removeAttribute("hidden");
    }
  }

  function marcar(linha, atributo, ativo) {
    if (ativo) {
      linha.setAttribute(atributo, "");
    } else {
      linha.removeAttribute(atributo);
    }
    aplicarVisibilidade(linha);
  }

  /* ---------------------------------------------------- hierarquia */

  /* Descendentes de uma linha: todas as linhas seguintes com nível maior,
     até encontrar uma de nível igual ou menor. */
  function descendentes(linhas, i) {
    var nivel = parseInt(linhas[i].getAttribute("data-nivel"), 10);
    var bloco = [];
    for (var j = i + 1; j < linhas.length; j++) {
      var n = parseInt(linhas[j].getAttribute("data-nivel"), 10);
      if (isNaN(n) || n <= nivel) break;
      bloco.push({ linha: linhas[j], nivel: n });
    }
    return bloco;
  }

  /* O "filho imediato" é o MENOR nível encontrado entre os descendentes —
     não necessariamente `nivel + 1`.

     A classificação orçamentária pula níveis: "DESPESAS CORRENTES" é nível
     1 e seu primeiro filho é "PESSOAL E ENCARGOS SOCIAIS", nível 3 — não
     existe nível 2 nesse ramo. Procurar exatamente `nivel + 1` não
     encontrava nada e a seta simplesmente não abria. */
  function nivelDosFilhos(bloco) {
    return bloco.reduce(function (menor, d) {
      return d.nivel < menor ? d.nivel : menor;
    }, Infinity);
  }

  function temFilhos(linhas, i) {
    return descendentes(linhas, i).length > 0;
  }

  function alternaFilhos(linhas, i, abrindo) {
    var bloco = descendentes(linhas, i);
    if (!bloco.length) return;
    var filho = nivelDosFilhos(bloco);

    bloco.forEach(function (d) {
      if (abrindo) {
        // abre só um degrau: os netos continuam recolhidos
        if (d.nivel === filho) marcar(d.linha, "data-recolhida", false);
      } else {
        marcar(d.linha, "data-recolhida", true);
        var sub = d.linha.querySelector(".loa-abridor");
        if (sub) {
          sub.textContent = "▸";
          sub.setAttribute("aria-expanded", "false");
        }
      }
    });
  }

  function preparaHierarquia(bloco) {
    var linhas = Array.prototype.slice.call(bloco.querySelectorAll("tbody tr"));
    if (!linhas.length || !linhas[0].hasAttribute("data-nivel")) return linhas;

    linhas.forEach(function (linha, i) {
      if (!temFilhos(linhas, i)) return;

      var rotulo = linha.querySelector(".loa-rotulo");
      if (!rotulo) return;

      var bloco = descendentes(linhas, i);
      var filho = nivelDosFilhos(bloco);
      var aberta = bloco.some(function (d) {
        return d.nivel === filho && !d.linha.hasAttribute("data-recolhida");
      });

      var abridor = document.createElement("button");
      abridor.type = "button";
      abridor.className = "loa-abridor";
      abridor.textContent = aberta ? "▾" : "▸";
      abridor.setAttribute("aria-expanded", aberta ? "true" : "false");
      abridor.setAttribute("aria-label", "Abrir ou fechar o detalhamento");
      rotulo.parentNode.insertBefore(abridor, rotulo);

      abridor.addEventListener("click", function () {
        var abrindo = abridor.getAttribute("aria-expanded") !== "true";
        alternaFilhos(linhas, i, abrindo);
        abridor.textContent = abrindo ? "▾" : "▸";
        abridor.setAttribute("aria-expanded", abrindo ? "true" : "false");
      });
    });

    return linhas;
  }

  /* --------------------------------------------------------- filtro */

  function aplicaFiltro(bloco, linhas, termo) {
    var busca = termo.toLowerCase().trim();
    var visiveis = 0;

    linhas.forEach(function (linha) {
      if (!busca) {
        // ao limpar, o filtro apenas se retira: a árvore volta ao estado
        // em que estava, porque nunca foi tocada.
        marcar(linha, "data-oculta-filtro", false);
        if (!linha.hasAttribute("data-recolhida")) visiveis++;
        return;
      }
      var achou = (linha.textContent || "").toLowerCase().indexOf(busca) !== -1;
      marcar(linha, "data-oculta-filtro", !achou);
      if (achou) visiveis++;
    });

    // Enquanto há texto no filtro, a árvore fica suspensa: procurar "saúde"
    // e não achar porque o ramo estava fechado seria desconcertante.
    linhas.forEach(function (linha) {
      marcar(
        linha,
        "data-recolhida",
        busca ? false : linha.dataset.arvoreFechada === "1",
      );
    });

    var contador = bloco.querySelector(".loa-contador");
    if (contador) {
      contador.textContent = busca
        ? visiveis + " de " + linhas.length + " linhas"
        : linhas.length + " linhas";
    }
  }

  /* ------------------------------------------------------ ordenação */

  function ordena(bloco, indice, tipo, cabecalho) {
    var corpo = bloco.querySelector("tbody");
    var linhas = Array.prototype.slice.call(corpo.querySelectorAll("tr"));
    var totais = linhas.filter(function (l) {
      return l.classList.contains("loa-total");
    });
    var dados = linhas.filter(function (l) {
      return !l.classList.contains("loa-total");
    });

    var crescente = cabecalho.getAttribute("aria-sort") !== "ascending";

    dados.sort(function (a, b) {
      var ca = a.cells[indice],
        cb = b.cells[indice];
      if (!ca || !cb) return 0;
      var r;
      if (tipo === "texto") {
        r = texto(ca).localeCompare(texto(cb), "pt-BR");
      } else {
        var na = numero(ca),
          nb = numero(cb);
        r = (isNaN(na) ? -Infinity : na) - (isNaN(nb) ? -Infinity : nb);
      }
      return crescente ? r : -r;
    });

    // ordenar desfaz a árvore: fora da ordem original o recuo mente
    dados.forEach(function (linha) {
      marcar(linha, "data-recolhida", false);
      linha.dataset.arvoreFechada = "0";
      corpo.appendChild(linha);
    });
    totais.forEach(function (linha) {
      corpo.appendChild(linha);
    });

    bloco.querySelectorAll(".loa-abridor").forEach(function (a) {
      a.hidden = true;
    });

    bloco.querySelectorAll("thead th").forEach(function (th) {
      th.setAttribute("aria-sort", "none");
    });
    cabecalho.setAttribute("aria-sort", crescente ? "ascending" : "descending");
  }

  /* ----------------------------------------------------- exportação */

  function exportaCSV(bloco) {
    var linhas = [];
    linhas.push(
      Array.prototype.map.call(bloco.querySelectorAll("thead th"), texto),
    );

    bloco.querySelectorAll("tbody tr").forEach(function (linha) {
      if (linha.hasAttribute("data-oculta-filtro")) return;
      linhas.push(Array.prototype.map.call(linha.cells, texto));
    });

    var csv = linhas
      .map(function (linha) {
        return linha
          .map(function (c) {
            return '"' + c.replace(/"/g, '""') + '"';
          })
          .join(";");
      })
      .join("\r\n");

    // BOM para o Excel abrir os acentos corretamente
    var blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = (bloco.getAttribute("data-id") || "tabela") + ".csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /* --------------------------------------------------------- ligação */

  function ativaTabela(bloco) {
    if (bloco.hasAttribute("data-pronto")) return;
    bloco.setAttribute("data-pronto", "");

    var linhas = preparaHierarquia(bloco);
    var dados = linhas.filter(function (l) {
      return !l.classList.contains("loa-total");
    });

    // guarda o estado inicial da árvore, para o filtro poder devolvê-lo
    dados.forEach(function (linha) {
      linha.dataset.arvoreFechada = linha.hasAttribute("data-recolhida")
        ? "1"
        : "0";
    });

    var contador = bloco.querySelector(".loa-contador");
    if (contador) contador.textContent = dados.length + " linhas";

    var filtro = bloco.querySelector(".loa-filtro");
    if (filtro) {
      var espera;
      filtro.addEventListener("input", function () {
        clearTimeout(espera);
        espera = setTimeout(function () {
          aplicaFiltro(bloco, dados, filtro.value);
        }, 120);
      });
    }

    bloco.querySelectorAll("thead th").forEach(function (th, i) {
      function acionar() {
        ordena(bloco, i, th.getAttribute("data-tipo"), th);
      }
      th.addEventListener("click", acionar);
      th.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          acionar();
        }
      });
    });

    var expandir = bloco.querySelector('[data-acao="expandir"]');
    if (expandir) {
      expandir.addEventListener("click", function () {
        var abrindo = expandir.dataset.estado !== "aberto";
        dados.forEach(function (linha) {
          // profundidade na árvore, não número do nível (que pula degraus)
          var prof = parseInt(linha.getAttribute("data-profundidade"), 10) || 1;
          var fechar = !abrindo && prof > 2;
          marcar(linha, "data-recolhida", fechar);
          linha.dataset.arvoreFechada = fechar ? "1" : "0";
        });
        bloco.querySelectorAll(".loa-abridor").forEach(function (a) {
          a.textContent = abrindo ? "▾" : "▸";
          a.setAttribute("aria-expanded", abrindo ? "true" : "false");
        });
        expandir.dataset.estado = abrindo ? "aberto" : "fechado";
        expandir.textContent = abrindo ? "Recolher tudo" : "Expandir tudo";
      });
    }

    var csv = bloco.querySelector('[data-acao="csv"]');
    if (csv)
      csv.addEventListener("click", function () {
        exportaCSV(bloco);
      });

    var imprimir = bloco.querySelector('[data-acao="imprimir"]');
    if (imprimir)
      imprimir.addEventListener("click", function () {
        window.print();
      });
  }

  /* ------------------------------------------------------------ mapa municipal */

  function normalizaMapa(nome) {
    return String(nome || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, " ")
      .trim()
      .replace(/\s+/g, " ");
  }

  function escaparHtml(valor) {
    return String(valor || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escaparSvg(valor) {
    return escaparHtml(valor);
  }

  function caminhoGeoJSON(geometry, projetar) {
    if (!geometry) return "";

    function anelParaPath(anel) {
      if (!anel || !anel.length) return "";
      return "M " + anel.map(function (ponto) {
        var p = projetar(ponto[0], ponto[1]);
        return p[0].toFixed(2) + " " + p[1].toFixed(2);
      }).join(" L ") + " Z";
    }

    if (geometry.type === "Polygon") {
      return geometry.coordinates.map(anelParaPath).join(" ");
    }

    if (geometry.type === "MultiPolygon") {
      return geometry.coordinates.map(function (poligono) {
        return poligono.map(anelParaPath).join(" ");
      }).join(" ");
    }

    return "";
  }

  function todosOsPontos(geometry, destino) {
    if (!geometry) return;

    function adicionarAnel(anel) {
      anel.forEach(function (ponto) {
        destino.push(ponto);
      });
    }

    if (geometry.type === "Polygon") {
      geometry.coordinates.forEach(adicionarAnel);
    } else if (geometry.type === "MultiPolygon") {
      geometry.coordinates.forEach(function (poligono) {
        poligono.forEach(adicionarAnel);
      });
    }
  }

  function escalaMapa(valor, valores) {
    if (!valores.length) return 0;
    var ordenados = valores.slice().sort(function (a, b) { return a - b; });
    if (ordenados.length === 1) return 5;

    var pos = ordenados.indexOf(valor);
    if (pos < 0) {
      pos = 0;
      for (var i = 0; i < ordenados.length; i++) {
        if (ordenados[i] <= valor) pos = i;
      }
    }

    return Math.min(5, Math.floor((pos / (ordenados.length - 1)) * 5));
  }

  function nomeFeature(feature) {
    var p = feature.properties || {};
    return p.name || p.nome || p.NM_MUN || p.NM_MUNICIP || p.description || "";
  }

  function idFeature(feature) {
    var p = feature.properties || {};
    return String(p.id || feature.id || p.CD_MUN || p.codarea || "").replace(/[^0-9]/g, "");
  }

  function criaTooltip(container) {
    var tooltip = document.createElement("div");
    tooltip.className = "loa-mapa-municipios__tooltip";
    tooltip.hidden = true;
    container.appendChild(tooltip);
    return tooltip;
  }

  function mostraTooltip(tooltip, container, nome, item, evento) {
    tooltip.innerHTML =
      '<strong>' + escaparHtml(nome) + '</strong>' +
      '<span>' + (item ? 'Investimento: ' + escaparHtml(item.valorFormatado) : 'Sem investimento localizado') + '</span>' +
      (item ? '<span>Participação: ' + escaparHtml(item.percentual) + '</span>' : '');

    tooltip.hidden = false;

    var rect = container.getBoundingClientRect();
    var x = evento.clientX - rect.left + 14;
    var y = evento.clientY - rect.top + 14;

    var limiteX = container.clientWidth - tooltip.offsetWidth - 8;
    var limiteY = container.clientHeight - tooltip.offsetHeight - 8;

    tooltip.style.left = Math.max(8, Math.min(x, limiteX)) + "px";
    tooltip.style.top = Math.max(8, Math.min(y, limiteY)) + "px";
  }

  function escondeTooltip(tooltip) {
    tooltip.hidden = true;
  }

  function montaMapaMunicipios(container) {
    if (container.hasAttribute("data-pronto")) return;
    container.setAttribute("data-pronto", "");

    var status = container.querySelector(".loa-mapa-municipios__status");
    var url = container.getAttribute("data-geojson-url");
    var bruto = container.getAttribute("data-map-data") || "[]";
    var dados;

    try {
      dados = JSON.parse(bruto);
    } catch (erro) {
      if (status) status.textContent = "Não foi possível ler os dados do mapa.";
      return;
    }

    var porNome = {};
    var porId = {};
    var valores = [];

    dados.forEach(function (item) {
      porNome[normalizaMapa(item.nome)] = item;
      if (item.id) porId[String(item.id)] = item;
      valores.push(Number(item.valor) || 0);
    });

    var tooltip = criaTooltip(container);

    function carregar(urlAtual) {
      return fetch(urlAtual, {
        mode: "cors",
        cache: "force-cache",
        headers: { "Accept": "application/geo+json, application/json" }
      }).then(function (resposta) {
        if (!resposta.ok) throw new Error("HTTP " + resposta.status);
        return resposta.json();
      });
    }

    carregar(url)
      .catch(function () {
        var fallback = container.getAttribute("data-geojson-fallback");
        if (!fallback) throw new Error("A malha municipal não respondeu.");
        return carregar(fallback);
      })
      .then(function (geo) {
        if (!geo || !geo.features || !geo.features.length) {
          throw new Error("A malha municipal veio vazia.");
        }

        var pontos = [];
        geo.features.forEach(function (feature) {
          todosOsPontos(feature.geometry, pontos);
        });

        if (!pontos.length) throw new Error("A malha municipal não possui geometria.");

        var minX = Infinity, maxX = -Infinity;
        var minY = Infinity, maxY = -Infinity;
        pontos.forEach(function (ponto) {
          minX = Math.min(minX, ponto[0]);
          maxX = Math.max(maxX, ponto[0]);
          minY = Math.min(minY, ponto[1]);
          maxY = Math.max(maxY, ponto[1]);
        });

        var largura = 1000;
        var altura = 700;
        var margem = 18;
        var escalaX = (largura - margem * 2) / Math.max(0.000001, maxX - minX);
        var escalaY = (altura - margem * 2) / Math.max(0.000001, maxY - minY);
        var escala = Math.min(escalaX, escalaY);
        var usadoX = (maxX - minX) * escala;
        var usadoY = (maxY - minY) * escala;
        var offsetX = (largura - usadoX) / 2;
        var offsetY = (altura - usadoY) / 2;

        function projetar(x, y) {
          return [
            offsetX + (x - minX) * escala,
            altura - (offsetY + (y - minY) * escala)
          ];
        }

        var cores = ["#f7eeee", "#f0caca", "#e7a0a0", "#d96b6b", "#b83d3d", "#7f1717"];
        var partes = [
          '<svg class="loa-mapa-municipios__svg" viewBox="0 0 ' + largura + ' ' + altura + '" role="img" aria-label="Mapa dos 853 municípios de Minas Gerais">'
        ];

        var ativos = 0;

        geo.features.forEach(function (feature) {
          var nome = nomeFeature(feature);
          var id = idFeature(feature);

          /* A malha geográfica do GitHub/IBGE traz o código IBGE no campo
             `properties.id` e o nome em `properties.name`. Usamos o código
             primeiro e o nome como fallback para evitar o mapa todo cinza
             quando a fonte geográfica mudar a forma dos atributos. */
          var item = porId[id] || porNome[normalizaMapa(nome)];
          var valor = item ? Number(item.valor) || 0 : 0;
          var faixa = item ? escalaMapa(valor, valores) : -1;
          var cor = faixa >= 0 ? cores[faixa] : "#e5e5e5";
          var d = caminhoGeoJSON(feature.geometry, projetar);
          if (!d) return;

          if (item) ativos++;

          var classe = item ? "loa-municipio loa-municipio--ativo" : "loa-municipio";
          var atributos =
            'class="' + classe + '"' +
            ' fill="' + cor + '"' +
            ' data-nome="' + escaparSvg(nome) + '"';

          if (item) {
            atributos +=
              ' data-href="' + escaparSvg(item.href) + '"' +
              ' tabindex="0"' +
              ' aria-label="' + escaparSvg(nome + ': ' + item.valorFormatado) + '"';
          } else {
            atributos += ' aria-label="' + escaparSvg(nome + ': sem investimento localizado') + '"';
          }

          partes.push('<path d="' + d + '" ' + atributos + '></path>');
        });

        partes.push("</svg>");
        container.innerHTML = partes.join("");
        container.appendChild(tooltip);

        if (status) status.remove();

        container.querySelectorAll(".loa-municipio").forEach(function (area) {
          var nome = area.getAttribute("data-nome") || "Município";
          var item = porNome[normalizaMapa(nome)];

          area.addEventListener("mouseenter", function (e) {
            mostraTooltip(tooltip, container, nome, item, e);
          });

          area.addEventListener("mousemove", function (e) {
            mostraTooltip(tooltip, container, nome, item, e);
          });

          area.addEventListener("mouseleave", function () {
            escondeTooltip(tooltip);
          });

          if (item) {
            function abrir() {
              window.location.href = area.getAttribute("data-href");
            }

            area.addEventListener("click", abrir);
            area.addEventListener("keydown", function (e) {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                abrir();
              }
            });
          }
        });

        container.setAttribute("data-municipios-com-investimento", String(ativos));
      })
      .catch(function (erro) {
        console.error("Mapa municipal:", erro);
        if (status) {
          status.textContent = "Não foi possível carregar a malha municipal de Minas Gerais.";
        }
      });
  }

  /* --------------------------------------------------------- versões */
  /*
     VERSÕES DO PROJETO
     -------------------
     O repositório volumes-loa ainda não possui tags oficiais. Por isso,
     v1.1 aparece aqui apenas como versão de demonstração da interface.

     QUANDO A EQUIPE DEFINIR AS TAGS OFICIAIS:
       1. substitua/adicone os itens desta lista;
       2. em cada item, troque `url` para /tree/<tag> (ou para a URL definida);
       3. marque a versão publicada em `atual`;
       4. não é necessário alterar o restante da integração.

     Exemplo futuro:
       { nome: "v1.1", url: "https://github.com/splor-mg/volumes-loa/tree/v1.1" }
  */
  var VERSAO_ATUAL = "v1.1";
  var VERSOES = [
    {
      nome: "v1.1",
      url: "https://github.com/splor-mg/loa-mg/tree/main",
      descricao: "Demonstração — tag oficial ainda não definida"
    }
  ];

  function criaIconeTag() {
  /*
     Ícone `material/tag` do Material for MkDocs.
     O SVG é inserido diretamente porque este seletor é criado pelo
     JavaScript depois que o template do Material já foi renderizado.
  */
  var span = document.createElement("span");
  span.className = "loa-versoes__icone md-icon";
  span.setAttribute("aria-hidden", "true");
  span.innerHTML =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" role="img">' +
    '<path d="M5.5 3C4.67 3 4 3.67 4 4.5v5.67c0 .4.16.78.44 1.06l8.33 8.33c.59.59 1.54.59 2.12 0l5.67-5.67c.59-.59.59-1.54 0-2.12l-8.33-8.33A1.49 1.49 0 0 0 11.17 3H5.5zm1.5 3.5A1.5 1.5 0 1 1 7 9.5 1.5 1.5 0 0 1 7 6.5z"/>' +
    '</svg>';
  return span;
}

  function montaVersoes() {
    var origem = document.querySelector(".md-header__source");
    if (!origem || document.querySelector(".loa-versoes")) return;

    var detalhes = document.createElement("details");
    detalhes.className = "loa-versoes";

    var resumo = document.createElement("summary");
    resumo.className = "loa-versoes__resumo";
    resumo.setAttribute("title", "Selecionar versão");
    resumo.appendChild(criaIconeTag());

    var rotulo = document.createElement("span");
    rotulo.className = "loa-versoes__atual";
    rotulo.textContent = VERSAO_ATUAL;
    resumo.appendChild(rotulo);
    detalhes.appendChild(resumo);

    var menu = document.createElement("div");
    menu.className = "loa-versoes__menu";
    menu.setAttribute("role", "menu");

    VERSOES.forEach(function (versao) {
      var item = document.createElement("a");
      item.className = "loa-versoes__item";
      item.href = versao.url;
      item.setAttribute("role", "menuitem");
      if (versao.nome === VERSAO_ATUAL) {
        item.classList.add("loa-versoes__item--atual");
      }

      var nome = document.createElement("strong");
      nome.textContent = versao.nome;
      item.appendChild(nome);

      var descricao = document.createElement("small");
      descricao.textContent = versao.descricao;
      item.appendChild(descricao);

      menu.appendChild(item);
    });

    detalhes.appendChild(menu);

    var observacao = document.createElement("div");
    observacao.className = "loa-versoes__observacao";
    observacao.textContent = "Tags oficiais do volumes-loa serão incorporadas aqui quando definidas.";
    menu.appendChild(observacao);

    /* Coloca o seletor imediatamente ao lado do bloco do GitHub. */
    origem.parentNode.insertBefore(detalhes, origem.nextSibling);
  }

  function ativarTudo() {
    document.querySelectorAll(".loa-tabela").forEach(ativaTabela);
    document.querySelectorAll(".loa-mapa-municipios").forEach(montaMapaMunicipios);
    montaVersoes();
  }

  /* `document$` é o fluxo do Material que emite a cada troca de página,
     incluindo as da navegação instantânea, que não recarrega o documento
     e portanto nunca dispara DOMContentLoaded de novo. */
  if (window.document$ && window.document$.subscribe) {
    window.document$.subscribe(ativarTudo);
  } else {
    document.addEventListener("DOMContentLoaded", ativarTudo);
  }
})();
