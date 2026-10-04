import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const root='/Users/jose/Documents/the-power/1-langGraph';
const skill='/Users/jose/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const tmp=root+'/.build/revision-intro';
const run=Date.now().toString();
const {finalizePresentation,resolvePresentationFont}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
const font=resolvePresentationFont({fontFamily:'Inter'});
const C={white:'#F4F7FF',muted:'#A7B7CC',cyan:'#25C5ED',violet:'#BA73FF',panel:'#111B31',border:'#314868'};
const sources='[Sources]\nhttps://docs.langchain.com/oss/python/langgraph/overview\nhttps://docs.langchain.com/oss/python/langchain/overview\nRepositorio app/soporte y ejercicios enviados a Laura. Logo thePower: asset original del deck de referencia, sin modificar.\n[/Sources]';
const decks=[
{id:'S5-langgraph',date:'5 octubre 2026 · 18:30–20:00',title:'LangGraph',subtitle:'Estado, decisiones y memoria',slides:[
 {kind:'cover',title:'LangGraph',body:'Estado, decisiones\ny memoria',seconds:30,notes:'Presentar el objetivo: diseñar el recorrido de un agente y construir un asistente de soporte. Esta presentación dura diez minutos y se cierra después. No explicar parámetros del proveedor ni ejecutar comandos todavía.'},
 {kind:'qr',title:'Antes de empezar',body:'Escanea el QR para valorar\nla clase anterior.',caption:'Hoy construiremos un agente de soporte por etapas.',seconds:45,notes:'Mostrar el QR original de AI Engineer y aclarar que evalúa la clase anterior. Dejar unos segundos para escanear. No es la entrega del ejercicio.'},
 {kind:'definition',title:'Qué es LangGraph',body:'Un framework para diseñar agentes\ncomo grafos con estado.',items:[['Estado','Datos que viajan durante la ejecución.'],['Decisiones','Rutas que el código hace explícitas.'],['Continuidad','Guardar y recuperar una conversación.']],seconds:75,notes:'Definir LangGraph como framework y runtime de orquestación. Un grafo puede combinar funciones deterministas y llamadas a modelos. Un nodo no tiene que ser un LLM. El modelo puede decidir una acción, pero el código define qué se puede ejecutar.'},
 {kind:'comparison',title:'LangChain y LangGraph',leftTitle:'LangChain',rightTitle:'LangGraph',left:['Componentes e integraciones:','modelos, mensajes y herramientas.','Agentes de mayor nivel con','un bucle ya preparado.'],right:['Diseño explícito del recorrido:','nodos, rutas y ciclos.','Control del estado y la','persistencia del agente.'],caption:'Se complementan: en esta clase combinaremos ambos.',seconds:120,notes:'No explicar LangChain como si solo permitiera flujos lineales: también ofrece agentes y sus abstracciones se apoyan en LangGraph. LangChain facilita componentes y agentes de nivel superior; con LangGraph dibujamos y controlamos explícitamente el flujo. Nuestro ejemplo usa mensajes y tools de LangChain dentro del grafo. LangGraph también puede utilizarse sin LangChain. Dedicar dos minutos a esta distinción.'},
 {kind:'building',title:'Cómo funciona un grafo',items:[['Estado','Mensajes, errores\ny presupuesto del turno.'],['Nodos','Funciones que leen\ny actualizan el estado.'],['Aristas','Conexiones que deciden\nqué paso se ejecuta.']],caption:'Si hace falta una herramienta, el flujo vuelve al modelo.',seconds:90,notes:'Explicar las tres piezas. Dibujar oralmente el ciclo chatbot → herramienta → chatbot y la ruta directa a la respuesta. El estado no es por sí solo memoria persistente; para conservarlo entre procesos usaremos un checkpointer.'},
 {kind:'case',title:'Qué vamos a construir',body:'Un asistente de soporte con\ndatos ficticios y dos herramientas.',items:[['Ticket','Consultar el estado de T-100.'],['Ayuda','Leer el artículo A-10 asociado.'],['Memoria','Continuar después de reiniciar.']],seconds:90,notes:'Presentar el caso sin enseñar aún el código. Una consulta de ticket sale de datos locales y verificables, no de la memoria del modelo. Las dos tools son consultar_ticket y buscar_articulo. Completaremos persistencia SQLite, separación de hilos y límites. No habrá frontend ni despliegue.'},
 {kind:'roadmap',title:'Cómo lo haremos',steps:['Grafo fijo','Chatbot','Tools','SQLite','Agente completo'],seconds:90,notes:'Explicar las cinco etapas del directo. Primero sin modelo, después mensajes, luego funciones de soporte, persistencia entre procesos y finalmente integración con límites. Los ejemplos principales comparten núcleo; las pruebas simuladas fuerzan errores y presupuesto sin consumir APIs. La TUI con juez/validador es una ampliación opcional.'},
 {kind:'finish',title:'Qué debe funcionar al terminar',items:[['Datos','Responder con el ticket\ny su artículo de ayuda.'],['Memoria','Recordar en el mismo hilo;\naislar otra conversación.'],['Control','Gestionar fallos y bloquear\nuna tercera herramienta.']],seconds:60,notes:'Cerrar la introducción a los diez minutos. Señalar el criterio de éxito: herramientas verificables, continuidad y aislamiento, límite y errores. Cerrar el modo presentación y continuar toda la práctica desde código/terminal. Los requisitos detallados y los comandos están en el guion privado y en el enunciado.'}
]},
{id:'S6-observabilidad',date:'7 octubre 2026 · 18:30–20:00',title:'Observabilidad',subtitle:'LangSmith + Langfuse',slides:[
 {kind:'cover',title:'Observabilidad',body:'LangSmith + Langfuse',seconds:30,notes:'Presentar la clase: observar el mismo agente del lunes, versionar sus prompts y comparar resultados. Presentación de diez minutos, antes de la práctica.'},
 {kind:'qr',title:'Antes de empezar',body:'Escanea el QR para valorar\nla clase anterior.',caption:'Hoy observaremos el agente que construimos el lunes.',seconds:45,notes:'Mostrar el QR de AI Engineer para evaluar la clase anterior. Aclarar que no es el ejercicio. Después, situar el agente de soporte de S5.'},
 {kind:'definition',title:'Qué es observabilidad',body:'Reconstruir qué ocurrió dentro\ndel agente a partir de su ejecución.',items:[['Recorrido','Qué pasos y herramientas utilizó.'],['Consumo','Cuánto tardó y cuántos tokens usó.'],['Resultado','Dónde falló y si respondió bien.']],seconds:75,notes:'Distinguir respuesta final de evidencia interna. La consola aporta un resumen, pero una plataforma conserva un árbol navegable de pasos. Latencia, tokens y errores son métricas; calidad requiere criterios y revisión.'},
 {kind:'comparison',title:'Dos plataformas, el mismo agente',leftTitle:'LangSmith',rightTitle:'Langfuse',left:['Trazas y evaluación de agentes.','Prompts y contexto de ejecución.','Seguiremos el árbol y los','mensajes del agente.'],right:['Trazas, sesiones y generaciones.','Prompts, métricas y evaluación.','Compararemos cómo localizar','el mismo caso.'],caption:'Capacidades compartidas; probaremos ambas sobre el mismo grafo.',seconds:90,notes:'Explicar qué mostraremos en cada interfaz sin presentar funciones compartidas como exclusivas. LangSmith y Langfuse permiten trazas, prompts y evaluación. Registraremos la misma ejecución, no construiremos dos agentes ni duplicaremos las llamadas al modelo por observar en dos sitios.'},
 {kind:'building',title:'Qué veremos en una traza',items:[['Consulta','Una raíz por petición\ny un hilo de conversación.'],['Pasos','Llamadas al modelo,\ntools y sus resultados.'],['Métricas','Tiempo, tokens, errores\ny coste con procedencia.']],caption:'Que exista una respuesta no significa que sea correcta.',seconds:90,notes:'Distinguir consulta, conversación, nodo y generación. Una petición puede hacer varias llamadas al modelo. Comprobar recepción remota y no solo que el proceso finalizó. El coste ausente no es cero y el coste inferido del panel puede diferir del proveedor.'},
 {kind:'case',title:'Qué vamos a hacer hoy',body:'Instrumentar el soporte del lunes\ny aprender a depurarlo con evidencia.',items:[['Registrar','Trazas en ambas plataformas.'],['Comparar','Dos prompts sobre diez consultas.'],['Depurar','Un fallo, un retraso y datos ocultos.']],caption:'Mismo código del agente; añadimos visibilidad y evaluación.',seconds:90,notes:'Presentar las capacidades que construiremos y mostraremos en la parte práctica. El lote de veinte respuestas ya está preparado. Durante el directo enseñaremos casos representativos para reservar tiempo a incidentes y privacidad. No se pide un panel propio ni Ragas.'},
 {kind:'roadmap',title:'Cómo lo haremos',steps:['Baseline','Trazas','Prompts','Comparar','Privacidad'],caption:'Ejecutar → observar → cambiar una versión → comparar con los mismos casos.',seconds:120,notes:'Explicar el recorrido práctico: baseline sin exportación, LangSmith y Langfuse, recuperación/aplicación de versiones fijas, comparación controlada y localización de incidentes. Conservar modelo/datos/parámetros y un hilo limpio por caso. No ajustar el prompt mirando el test. El filtrado protege las trazas antes de exportar; no filtra automáticamente lo enviado al modelo.'},
 {kind:'finish',title:'Qué debe quedar demostrado',items:[['Trazabilidad','Relacionar una respuesta con\nsu recorrido y su prompt.'],['Comparación','Interpretar métricas y fallos\nsin ocultar resultados.'],['Privacidad','Leer los datos filtrados\nen ambas plataformas.']],caption:'Pasamos a la terminal y a las plataformas. La presentación termina aquí.',seconds:60,notes:'Cerrar a los diez minutos. Pasar al baseline del agente en la terminal y mantener el resto de la clase en código, resultados y las plataformas. Los comandos, el ejercicio y las incidencias están en el guion privado. No volver continuamente al deck.'}
]}];
await fs.writeFile(tmp+'/intro-specs.json',JSON.stringify(decks,null,2));
const primitives=[];
function add(slide,deckIndex,slideIndex,kind,options){primitives.push({deck:deckIndex,slide:slideIndex,kind,...options});if(kind==='image')return slide.images.add(options);const x=slide.shapes.add(options);return x;}
function text(s,di,si,value,x,y,w,h,size=30,bold=false,color=C.white){const shape=add(s,di,si,'shape',{geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});shape.text=value;shape.text.style={typeface:font,fontSize:size,bold,color,autoFit:'none'};primitives.at(-1).text=value;primitives.at(-1).textStyle={typeface:font,fontSize:size,bold,color};}
function shape(s,di,si,x,y,w,h,fill=C.panel,line=C.border,geometry='roundRect'){return add(s,di,si,'shape',{geometry,position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:1.5},...(geometry==='ellipse'?{}:{borderRadius:12})});}
function centerCoverLabel(s,di,si,value,y){
 text(s,di,si,value,948,y,200,95,28,true);
 const label=s.shapes.items.at(-1);
 label.text.alignment='center';label.text.verticalAlignment='middle';
 label.text.insets={top:0,right:0,bottom:0,left:0};
 primitives.at(-1).textStyle.alignment='center';primitives.at(-1).textStyle.verticalAlignment='middle';
 primitives.at(-1).textStyle.insets={top:0,right:0,bottom:0,left:0};
}
for(let di=0;di<decks.length;di++){
 const d=decks[di], sourcePath=root+'/material/presentaciones/'+d.id+'.pptx';
 const refSha=crypto.createHash('sha256').update(await fs.readFile(sourcePath)).digest('hex');
 const p=await PresentationFile.importPptx(await FileBlob.load(sourcePath));
 // La reescritura cambia todos los roles del deck; conservar masters/theme del original.
 const oldCount=p.slides.items.length;
 for(let i=0;i<d.slides.length;i++){
  const spec=d.slides[i];const s=p.slides.add({layoutId:'/ppt/slideLayouts/slideLayout1.xml'});
  add(s,di,i,'image',{blob:new Uint8Array(await fs.readFile(root+'/material/assets/fondo-thepower.png')),contentType:'image/png',alt:'Fondo original azul oscuro',position:{left:0,top:0,width:1280,height:720},fit:'contain'});primitives.at(-1).asset='background';delete primitives.at(-1).blob;
  const logoPosition=spec.kind==='cover'?{left:60,top:35,width:260,height:82}:{left:56,top:647,width:145,height:46};
  add(s,di,i,'image',{blob:new Uint8Array(await fs.readFile(root+'/material/assets/thepower-logo.png')),contentType:'image/png',alt:'Logo original thePower',position:logoPosition,fit:'contain'});primitives.at(-1).asset='logo';delete primitives.at(-1).blob;
  if(spec.kind==='cover'){
   text(s,di,i,spec.title,58,162,760,88,64,true);
   text(s,di,i,spec.body,58,273,765,143,44,true,C.muted);
   if(di!==0)text(s,di,i,'Introducción · 10 minutos',65,477,740,55,26,false,C.cyan);
   text(s,di,i,d.date,65,545,740,55,27,true,C.cyan);
   text(s,di,i,'AI Engineer · José Antonio Nuevo',65,650,740,37,23,false,C.muted);
   shape(s,di,i,948,158,200,95,C.panel,C.cyan,'ellipse');if(di===0)centerCoverLabel(s,di,i,'Estado',158);else text(s,di,i,'Consulta',968,188,162,55,28,true);
   shape(s,di,i,948,340,200,95,C.panel,'#5E85FF','ellipse');if(di===0)centerCoverLabel(s,di,i,'Modelo',340);else text(s,di,i,'Traza',968,370,162,55,28,true);
   text(s,di,i,'↓',1010,269,60,59,40,false,C.cyan);
   shape(s,di,i,948,522,200,95,C.panel,C.violet,'ellipse');if(di===0)centerCoverLabel(s,di,i,'Tools',522);else text(s,di,i,'Evidencia',968,552,162,55,28,true);
   text(s,di,i,'↓',1010,451,60,59,40,false,C.violet);
  }else{
   text(s,di,i,spec.title,57,46,1162,105,47,true);
   text(s,di,i,`${di===0?'S5':'S6'} · AI Engineer   ${String(i+1).padStart(2,'0')}/08`,970,657,260,36,17,false,C.muted);
   if(spec.kind==='qr'){
    text(s,di,i,spec.body,62,236,680,185,37,true);
    text(s,di,i,spec.caption,62,469,660,104,30,false,C.muted);
    add(s,di,i,'image',{blob:new Uint8Array(await fs.readFile(root+'/material/assets/qr-ai-engineer.jpg')),contentType:'image/jpeg',alt:'QR original de evaluación de AI Engineer',position:{left:820,top:211,width:360,height:360},fit:'contain'});primitives.at(-1).asset='qr';delete primitives.at(-1).blob;
   }else if(spec.kind==='comparison'){
    shape(s,di,i,58,188,552,353);shape(s,di,i,670,188,552,353);
    text(s,di,i,spec.leftTitle,80,208,510,68,36,true,C.cyan);text(s,di,i,spec.rightTitle,692,208,510,68,36,true,C.violet);
    text(s,di,i,spec.left.join('\n'),80,301,510,222,28);text(s,di,i,spec.right.join('\n'),692,301,510,222,28);
    text(s,di,i,spec.caption,62,578,1150,63,27,false,C.muted);
   }else if(spec.kind==='definition'||spec.kind==='case'){
    text(s,di,i,spec.body,61,179,1140,129,38,true);
    const y=spec.kind==='case'?330:335;
    spec.items.forEach((it,j)=>{text(s,di,i,it[0],62,y+j*82,235,70,29,true,[C.cyan,C.violet,'#FF78C4'][j]);text(s,di,i,it[1],320,y+j*82,880,70,29);});
    if(spec.caption)text(s,di,i,spec.caption,62,603,1140,48,25,false,C.muted);
   }else if(spec.kind==='building'||spec.kind==='finish'){
    spec.items.forEach((it,j)=>{const x=58+j*405;shape(s,di,i,x,222,370,306);text(s,di,i,it[0],x+22,251,326,69,34,true,[C.cyan,C.violet,'#FF78C4'][j]);text(s,di,i,it[1],x+22,347,326,168,29);});
    if(spec.caption)text(s,di,i,spec.caption,62,577,1150,66,27,false,C.muted);
   }else if(spec.kind==='roadmap'){
    spec.steps.forEach((step,j)=>{const x=57+j*239;shape(s,di,i,x,262,210,145);
     if(di===0){
      text(s,di,i,String(j+1),x+24,282,162,40,25,true,C.cyan);
      const number=s.shapes.items.at(-1);number.text.insets={top:0,right:0,bottom:0,left:0};number.text.verticalAlignment='top';
      text(s,di,i,step==='Agente completo'?'Agente\ncompleto':step,x+24,322,162,64,26,true);
      const label=s.shapes.items.at(-1);label.text.insets={top:0,right:0,bottom:0,left:0};label.text.verticalAlignment='middle';
     }else{
      text(s,di,i,String(j+1),x+15,277,60,55,25,true,C.cyan);text(s,di,i,step,x+15,340,180,58,26,true);
     }if(j<4)add(s,di,i,'shape',{geometry:'rightArrow',position:{left:x+215,top:328,width:18,height:14},fill:C.cyan,line:{fill:'none',width:0}});});
    if(spec.caption)text(s,di,i,spec.caption,62,464,1150,122,31,false,C.muted);
   }
  }
  s.speakerNotes.textFrame.setText(`INTRODUCCIÓN · ${spec.seconds} segundos.\n${spec.notes}\n\nDespués de la diapositiva 8, cerrar la presentación y seguir el guion práctico.\n\n${sources}`);
 }
 for(let k=oldCount-1;k>=0;k--)p.slides.remove(k);
 const build=tmp+'/final-'+run;await fs.mkdir(build,{recursive:true});
 const candidate=build+'/'+d.id+'-candidate.pptx';await(await PresentationFile.exportPptx(p)).save(candidate);
 await fs.mkdir(build+'/output',{recursive:true});
 const out=build+'/output/'+d.id+'.pptx';
 await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:out,pythonExecutable:'/Users/jose/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:8,fontPolicy:{basis:'reference',families:[font],referencePath:sourcePath,referenceSha256:refSha},verifyArtifactToolImport:true,receiptPath:build+'/'+d.id+'-validation.json'});
 const render=build+'/render-'+d.id;await fs.mkdir(render,{recursive:true});
 for(let i=0;i<8;i++){const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(render+'/slide-'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await blob.arrayBuffer()));}
 console.log(d.id,build);
}
await fs.writeFile(tmp+'/primitives.json',JSON.stringify(primitives,null,2));
