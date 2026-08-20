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

  function escaparSvg(valor) {
    return String(valor || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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
      var menor = 0;
      for (var i = 0; i < ordenados.length; i++) {
        if (ordenados[i] <= valor) menor = i;
      }
      pos = menor;
    }

    return Math.min(5, Math.floor((pos / (ordenados.length - 1)) * 5));
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
    var valores = [];
    dados.forEach(function (item) {
      porNome[normalizaMapa(item.nome)] = item;
      valores.push(Number(item.valor) || 0);
    });

    function carregar(urlAtual) {
      return fetch(urlAtual, { mode: "cors", cache: "force-cache" })
        .then(function (resposta) {
          if (!resposta.ok) throw new Error("HTTP " + resposta.status);
          return resposta.json();
        });
    }

    carregar(url).catch(function () {
      var fallback = container.getAttribute("data-geojson-fallback");
      if (!fallback) throw new Error("A malha do IBGE não respondeu.");
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
        var escalaX = (largura - margem * 2) / (maxX - minX);
        var escalaY = (altura - margem * 2) / (maxY - minY);
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
          '<svg class="loa-mapa-municipios__svg" viewBox="0 0 ' + largura + ' ' + altura + '" aria-label="Mapa dos municípios de Minas Gerais">'
        ];

        geo.features.forEach(function (feature) {
          var propriedades = feature.properties || {};
          var nome = propriedades.name || propriedades.nome || propriedades.NM_MUNICIP || propriedades.NM_MUN || "";
          var item = porNome[normalizaMapa(nome)];
          var valor = item ? Number(item.valor) || 0 : 0;
          var faixa = item ? escalaMapa(valor, valores) : -1;
          var cor = faixa >= 0 ? cores[faixa] : "#eeeeee";
          var d = caminhoGeoJSON(feature.geometry, projetar);
          if (!d) return;

          var classe = item ? "loa-municipio loa-municipio--ativo" : "loa-municipio";
          var atributos = 'class="' + classe + '" fill="' + cor + '" data-nome="' + escaparSvg(nome) + '"';

          if (item) {
            atributos += ' data-href="' + escaparSvg(item.href) + '" tabindex="0"';
          }

          partes.push('<path d="' + d + '" ' + atributos + '><title>' + escaparSvg(
            item
              ? nome + ": " + item.valorFormatado + " (" + item.percentual + ")"
              : nome + ": sem investimento localizado"
          ) + '</title></path>');
        });

        partes.push("</svg>");
        container.innerHTML = partes.join("");

        container.querySelectorAll("[data-href]").forEach(function (area) {
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
        });
      })
      .catch(function (erro) {
        console.error("Mapa municipal:", erro);
        if (status) {
          status.innerHTML =
            "Não foi possível carregar a malha municipal de Minas Gerais. " +
            "Verifique se o navegador consegue acessar a API pública do IBGE.";
        }
      });
  }

  function ativarTudo() {
    document.querySelectorAll(".loa-tabela").forEach(ativaTabela);
    document.querySelectorAll(".loa-mapa-municipios").forEach(montaMapaMunicipios);
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
