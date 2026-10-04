# Presentaciones introductorias · versión del 04/10/2026

Las dos presentaciones son **ocho diapositivas para los diez primeros minutos**. Las notas distribuyen 600 segundos por clase. Después se cierra el PowerPoint y se sigue el guion práctico. No añadir comandos de las demos ni slides para acompañar cada bloque de los 90 minutos.

`build-presentaciones.mjs` y `slide-specs.json` contienen el generador y el contenido actualizado. Se reutilizan el fondo, tipografía y logo originales. Los assets permanentes están en `material/assets/fondo-thepower.png`, `thepower-logo.png` y `qr-ai-engineer.jpg`.

Para regenerar en este Mac: copiar el generador a `.build/revision-intro/build-intros.mjs`, crear ese directorio y enlazar `node_modules` con los paquetes del runtime de Codex. Ejecutar con Node y `RUNTIME_NODE`, `RUNTIME_NODE_MODULES`, `RUNTIME_BIN_DIR` devueltos por `load_workspace_dependencies`. El generador importa las presentaciones locales para conservar tema/masters, produce candidatos y finales en un directorio nuevo y renderiza los ocho slides. Revisar los renders antes de copiar los PPTX validados a `material/presentaciones`.

Las ediciones de Google Slides se actualizaron en los mismos enlaces. Se leyó su estructura tras la edición y se exportaron los PDF completos de ocho páginas para verificar todas las diapositivas. Los PDF entregados son esa exportación nativa, no capturas pegadas en un PDF.

La versión anterior de quince diapositivas se conserva en `version-previa-intro-2026-10-04/`. La documentación de pruebas de código mantiene su fecha original; esta revisión corrige el material docente y su uso durante el directo.
