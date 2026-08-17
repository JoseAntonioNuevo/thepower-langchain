# Lección 01 — Un grafo es funciones + aristas

Esta primera lección elimina el LLM para enseñar la mecánica esencial de
LangGraph. El programa recibe `hola thepower`, ejecuta una función y termina:

```bash
python langgraph/01_grafo.py
```

No hace falta `OPENROUTER_API_KEY`, Tavily ni `.env`.

## La idea: estado, nodos y aristas

Un grafo de LangGraph tiene tres piezas:

- **Estado**: datos compartidos que pasan de nodo a nodo.
- **Nodo**: una función que lee el estado y devuelve cambios.
- **Arista**: una conexión que decide qué nodo se ejecuta después.

En esta lección el estado es mínimo:

```python
class State(TypedDict):
    texto: str
```

El nodo `mayusculas` no devuelve todo el estado. Devuelve un parche:

```python
def mayusculas(state: State) -> dict:
    return {"texto": state["texto"].upper()}
```

LangGraph mezcla ese resultado con el estado anterior. La entrada conserva
`texto`, pero su valor pasa de `hola thepower` a `HOLA THEPOWER`.

## Cómo se construye

```python
builder = StateGraph(State)
builder.add_node("mayusculas", mayusculas)
builder.add_edge(START, "mayusculas")
builder.add_edge("mayusculas", END)
graph = builder.compile()
```

`StateGraph(State)` declara la forma del estado. `add_node` registra la
función con un nombre. `START` y `END` son los puntos oficiales de entrada y
salida. `compile()` convierte el diseño en un grafo ejecutable.

La ejecución es una llamada normal:

```python
resultado = graph.invoke({"texto": "hola thepower"})
```

El recorrido es determinista:

```text
START → mayusculas → END
```

## Qué no aparece todavía

| Esta lección usa | Todavía no usa |
|---|---|
| `StateGraph`, `START`, `END` | LLM |
| `TypedDict` | API keys |
| Una función Python como nodo | Tools |
| `invoke()` | Memoria |
| `ui.consola` para enseñar la salida | TUI |

Esto es intencionado. Antes de añadir decisiones probabilísticas conviene
entender el flujo que controla el programa.

## Qué pinta la consola

[`ui/consola.py`](../../ui/consola.py) no participa en el grafo.
Solo hace más visible la demo:

- `banner()` muestra el número y duración de la lección;
- `grafo_ascii()` dibuja `START → mayusculas → END`;
- `panel()` imprime el estado antes y después;
- el color se desactiva si no hay TTY o si existe `NO_COLOR`.

Por eso se puede probar el grafo sin simular una terminal. La presentación está
separada de la lógica.

## Qué ocurre si añadimos otro nodo

Una arista fija puede encadenar más funciones:

```text
START → normalizar → mayusculas → END
```

Cada nodo leería el estado recibido y devolvería solo las claves que cambia.
Cuando más adelante aparezcan aristas condicionales, la diferencia será que
la siguiente arista se calcula a partir del estado, en vez de estar fijada de
antemano.

## Mapa de ficheros

| Fichero | Papel |
|---|---|
| [`langgraph/01_grafo.py`](../../langgraph/01_grafo.py) | Construye y ejecuta el ejemplo mínimo |
| [`ui/consola.py`](../../ui/consola.py) | Salida didáctica para scripts |
| [`tests/test_consola.py`](../../tests/test_consola.py) | Comprueba banners, paneles, color y spinner |

El siguiente paso es sustituir la función aislada por un modelo que pueda
pedir una herramienta: [`02_tools.md`](02_tools.md).
