/*
 * WR - MPPP - JS - Comandos
 *
 * Los botones de la barra de comandos de Fila y Solicitud (inventario 12.5).
 * Son comandos CLASICOS con web resource JavaScript (DA-02, corregida el
 * 2026-09-22): un comando moderno no se puede crear por API.
 *
 * LA LOGICA NO VIVE ACA (DA-07). Un boton solo escribe `sanic_estado` /
 * `sanic_estadoprocesamiento`. Que la transicion sea valida, quien puede
 * hacerla y la segregacion de funciones los decide el plugin de transicion
 * (`03` seccion 4). Un usuario que llame al Web API sin pasar por la app
 * encuentra las mismas reglas.
 *
 * Accion masiva: el ribbon pasa `SelectedControlSelectedItemIds`, igual que
 * Power Fx pasaria `Self.Selected.AllItems`. Una tanda puede fallar en unas
 * filas y en otras no (por ejemplo, el supervisor intenta aprobar una fila que
 * el mismo digito): se informa cuantas se aplicaron y cuales no y por que, y
 * nunca se deja una fila a medias.
 *
 * EL DIALOGO DE MOTIVO (DA-03, corregida el 2026-09-23). Los comandos que piden
 * un texto abren el formulario de CREACION RAPIDA de
 * `sanic_mppp_tbl_motivoaccion` con `openForm` y `useQuickCreateForm`.
 *
 * NO es una pagina custom, y no por gusto: `navigateTo` a una pagina custom
 * resuelve el promise SIN NINGUN VALOR al cerrar el dialogo, asi que la pagina
 * no tendria como devolver el motivo; y su `pageInput` solo admite un
 * `recordId` que debe ser un GUID, asi que tampoco podria recibir las 25 filas
 * seleccionadas.
 *
 * Y tampoco es el formulario PRINCIPAL en un modal, que es lo que hacia hasta el
 * 2026-09-23 con `pageType: "entityrecord"`. Esa variante funcionaba, pero traia
 * el formulario entero adentro del dialogo: barra de comandos, titulo de
 * registro, pestaña y la barra de Copilot, para pedir una linea de texto. La
 * creacion rapida devuelve `savedEntityReference` igual (ver `pedirMotivo`).
 *
 * El registro de motivo es TRANSPORTE, no dato de negocio: se lee y se borra.
 * El texto queda en `sanic_mensaje` de cada fila (o en `sanic_motivorevision`
 * de la solicitud, que el plugin pasa a la Bitacora).
 */
var Sanic = Sanic || {};
Sanic.Mppp = Sanic.Mppp || {};

Sanic.Mppp.Comandos = (function () {
    "use strict";

    // Valores reales del entorno (leidos de la metadata el 2026-09-22), no de memoria.
    //
    // OJO con el nombre de la tabla. `Xrm.WebApi.updateRecord` pide el nombre
    // LOGICO (`sanic_mppp_tbl_fila`), no el del conjunto de entidades
    // (`sanic_mppp_tbl_filas`, con ese). Hasta el 2026-09-23 esto decia el del
    // conjunto y TODOS los comandos que cambian estado fallaban con
    // "The entity 'sanic_mppp_tbl_filas' cannot be found", un error que solo
    // aparece al apretar el boton: al guardar el web resource no lo ve nadie.
    var FILA = {
        tabla: "sanic_mppp_tbl_fila",
        columna: "sanic_estado",
        mensaje: "sanic_mensaje",
        VALIDADA: 159460003,
        DIGITADA: 159460004,
        APROBADA: 159460005,
        RECHAZADA_AS400: 159460006,
        ANULADA: 159460007
    };
    var SOLICITUD = {
        tabla: "sanic_mppp_tbl_solicitud",
        columna: "sanic_estadoprocesamiento",
        CERRADA: 159460007,
        DESCARTADA: 159460003
    };
    var MOTIVO = { tabla: "sanic_mppp_tbl_motivoaccion", columna: "sanic_motivo" };

    /*
     * DESDE QUE ESTADO SE PUEDE HACER CADA ACCION. Unica copia en el cliente.
     *
     * No contradice DA-07 ("la logica no vive aca") por una asimetria que hay que
     * tener presente: **esto solo OCULTA**. La autoridad sigue siendo
     * `Dominio/TransicionesDeFila.cs`, que corre en el servidor y rechaza igual.
     *   - si aca se muestra de mas, el plugin rechaza y no pasa nada grave;
     *   - si aca se oculta de mas, el usuario no puede trabajar y no sabe por que.
     * Por eso, ANTE LA DUDA SE MUESTRA (ver `algunaAdmite`).
     *
     * Este mapa es una COPIA de la tabla del dominio y puede divergir de ella sin
     * que nada se queje: ninguna prueba unitaria puede cruzar C# con JavaScript.
     * Lo verifica `herramientas/pruebas/verificar_transiciones.py`, que lee las dos
     * y las compara. Si se agrega una transicion al dominio, hay que tocar esto.
     */
    var TRANSICIONES_VALIDAS = {
        digitada: [FILA.VALIDADA],
        aprobar: [FILA.DIGITADA],
        devolver: [FILA.DIGITADA],
        rechazadaas400: [FILA.VALIDADA, FILA.DIGITADA],
        anular: [FILA.VALIDADA, FILA.DIGITADA]
    };

    // En el XML del ribbon la plataforma sustituye por idioma; acá no. Por eso
    // cada texto lleva su version en los dos idiomas del proyecto.
    var TEXTOS = {
        1033: {
            confirmar: "Apply \"{accion}\" to {n} selected row(s)?",
            titulo: "Confirm",
            si: "Apply",
            no: "Cancel",
            listo: "{ok} of {n} row(s) updated.",
            conFallas: "{ok} of {n} row(s) updated. {mal} could not be updated:",
            ninguna: "No rows were selected.",
            cerrar: "OK",
            sinMotivo: "No reason was entered. Nothing was changed.",
            progreso: "Applying \"{accion}\"\u2026 {hechas} of {n}"
        },
        3082: {
            confirmar: "¿Aplicar \"{accion}\" a {n} fila(s) seleccionada(s)?",
            titulo: "Confirmar",
            si: "Aplicar",
            no: "Cancelar",
            listo: "{ok} de {n} fila(s) actualizada(s).",
            conFallas: "{ok} de {n} fila(s) actualizada(s). {mal} no se pudieron actualizar:",
            ninguna: "No hay ninguna fila seleccionada.",
            cerrar: "Aceptar",
            sinMotivo: "No se escribio ningun motivo. No se cambio nada.",
            progreso: "Aplicando \"{accion}\"\u2026 {hechas} de {n}"
        }
    };

    function idioma() {
        try {
            var lcid = Xrm.Utility.getGlobalContext().userSettings.languageId;
            return TEXTOS[lcid] ? TEXTOS[lcid] : TEXTOS[1033];
        } catch (e) {
            return TEXTOS[1033];
        }
    }

    function armar(plantilla, valores) {
        var texto = plantilla;
        for (var clave in valores) {
            if (Object.prototype.hasOwnProperty.call(valores, clave)) {
                texto = texto.split("{" + clave + "}").join(valores[clave]);
            }
        }
        return texto;
    }

    // Un id puede llegar con llaves segun desde donde se invoque el comando.
    function limpiarId(id) {
        return String(id).replace("{", "").replace("}", "");
    }

    function refrescar(control) {
        try {
            if (control && typeof control.refresh === "function") {
                control.refresh();
            }
        } catch (e) {
            // Que no se pueda refrescar la grilla no invalida lo que ya se escribio.
        }
    }

    /*
     * Aplica el mismo cambio a cada fila con UNA PETICION POR FILA, en paralelo.
     *
     * Una peticion por fila y no un lote, a proposito: una fila que el plugin
     * rechaza no tiene por que arrastrar a las demas, y asi se informa el motivo
     * de cada rechazo por separado.
     *
     * EN PARALELO, tambien a proposito: con 100 filas la tanda tarda unos 10
     * segundos asi, y encadenadas tardaria varias veces mas con la pantalla
     * esperando. Hasta el 2026-09-23 este comentario decia "UNA POR UNA", que
     * suena secuencial y no lo es; sobre esa frase se tomaron decisiones
     * equivocadas (se copio incluso a otra herramienta del proyecto).
     *
     * Que las filas viajen concurrentes tiene una consecuencia del lado del
     * servidor: dos transiciones de la MISMA Solicitud podrian leer su estado a
     * medias. Eso NO se arregla aca sino en el plugin, que toma el bloqueo de la
     * Solicitud antes de mirar sus filas (`PlomeriaDeFila.TomarElBloqueoDeLaSolicitud`).
     *
     * `alAvanzar` recibe cuantas terminaron, para el indicador de progreso.
     * Devuelve el detalle de las que fallaron.
     */
    function aplicar(tabla, ids, cambio, alAvanzar) {
        var hechas = 0;
        function avanzar() {
            hechas = hechas + 1;
            if (alAvanzar) {
                alAvanzar(hechas);
            }
        }
        var resultados = ids.map(function (id) {
            return Xrm.WebApi.updateRecord(tabla, limpiarId(id), cambio).then(
                function () { avanzar(); return null; },
                function (error) { avanzar(); return (error && error.message) || String(error); }
            );
        });
        return Promise.all(resultados).then(function (fallas) {
            return fallas.filter(function (f) { return f !== null; });
        });
    }

    /*
     * Corre `tarea()` con el indicador de progreso arriba, y lo CIERRA PASE LO QUE PASE.
     *
     * Learn avisa en negrita sobre `showProgressIndicator`: "el dialogo de progreso
     * BLOQUEA LA INTERFAZ hasta que se cierra con closeProgressIndicator". O sea que
     * un error que escape sin cerrarlo deja al usuario con la aplicacion muerta y sin
     * mas salida que recargar la pagina. Por eso el cierre va en los DOS caminos del
     * `then`, y por eso `mostrar` y `cerrar` se trapean: que el indicador no ande no
     * puede impedir que la operacion siga ni que se libere la pantalla.
     *
     * Con 100 filas la tanda tarda unos 10 segundos (medido en Dev el 2026-09-23), y
     * sin esto el usuario no tiene ninguna senal de que algo esta pasando.
     */
    function conProgreso(mensajeInicial, tarea) {
        mostrarProgreso(mensajeInicial);
        var listo = false;
        function cerrar() {
            if (!listo) {
                listo = true;
                cerrarProgreso();
            }
        }
        return tarea().then(
            function (valor) { cerrar(); return valor; },
            function (error) { cerrar(); throw error; }
        );
    }

    function mostrarProgreso(mensaje) {
        try {
            Xrm.Utility.showProgressIndicator(mensaje);
        } catch (e) {
            // Sin indicador se trabaja igual; sin poder cerrarlo, no.
        }
    }

    function cerrarProgreso() {
        try {
            Xrm.Utility.closeProgressIndicator();
        } catch (e) {
            // `closeProgressIndicator` no hace nada si no hay dialogo abierto (Learn).
        }
    }

    function ejecutar(nombreAccion, tabla, cambio, ids, control) {
        var t = idioma();
        if (!ids || !ids.length) {
            return Xrm.Navigation.openAlertDialog({ text: t.ninguna, confirmButtonLabel: t.cerrar });
        }
        var total = ids.length;
        return Xrm.Navigation.openConfirmDialog(
            {
                title: t.titulo,
                text: armar(t.confirmar, { accion: nombreAccion, n: total }),
                confirmButtonLabel: t.si,
                cancelButtonLabel: t.no
            }
        ).then(function (respuesta) {
            if (!respuesta || !respuesta.confirmed) {
                return null;
            }
            return conProgreso(
                armar(t.progreso, { accion: nombreAccion, hechas: 0, n: total }),
                function () {
                    return aplicar(tabla, ids, cambio, function (hechas) {
                        mostrarProgreso(armar(t.progreso, { accion: nombreAccion, hechas: hechas, n: total }));
                    });
                }
            ).then(function (fallas) {
                refrescar(control);
                var ok = total - fallas.length;
                var texto = fallas.length
                    ? armar(t.conFallas, { ok: ok, n: total, mal: fallas.length }) + "\n\n" + fallas.join("\n")
                    : armar(t.listo, { ok: ok, n: total });
                return Xrm.Navigation.openAlertDialog({ text: texto, confirmButtonLabel: t.cerrar });
            });
        });
    }

    /*
     * Los estados de las filas SELECCIONADAS, leidos de la grilla que ya esta en
     * pantalla: `sanic_estado` es una columna de la vista, asi que el dato ya viajo
     * y no hace falta ir al servidor. Eso importa porque una EnableRule se evalua en
     * CADA cambio de seleccion: una consulta ahi haria la grilla inusable.
     *
     * `null` si no se pudo averiguar (otra vista, la grilla todavia cargando, una
     * version distinta del control). Quien llama decide, y decide MOSTRAR.
     */
    /*
     * DIAGNOSTICO TEMPORAL (2026-09-23). Se saca cuando sepamos por que las reglas
     * no ocultan los botones en la grilla principal. Tres intentos a ciegas ya
     * costaron tres pruebas al usuario; esto imprime lo que la funcion VE, que es
     * lo unico que no estabamos mirando.
     */
    function traza(etapa, dato) {
        try {
            console.log("[MPPP reglas] " + etapa + ":", dato);
        } catch (e) {
            // una consola que no existe no puede romper un comando
        }
    }

    /* Los nombres que expone un objeto, funciones marcadas con (). Es lo unico que
     * distingue "el metodo no existe" de "el metodo existe y devuelve vacio", y esa
     * diferencia es justamente la que no teniamos. */
    function claves(objeto) {
        var nombres = [];
        try {
            for (var n in objeto) {
                nombres.push(n + (typeof objeto[n] === "function" ? "()" : ""));
            }
        } catch (e) {
            return "(no se pudo inspeccionar: " + (e && e.message) + ")";
        }
        return nombres.join(", ");
    }

    /* `getSelectedRows()` devuelve una Collection, no un array. `forEach` es suyo y
     * no siempre recorre; `getAll()` e indices son los otros dos caminos. Se prueban
     * los tres porque cual funciona depende del tipo de grilla. */
    function filasDeLaGrilla(grid) {
        var coleccion = grid.getSelectedRows();
        traza("coleccion de seleccionadas", claves(coleccion));

        if (coleccion && typeof coleccion.getAll === "function") {
            var todas = coleccion.getAll();
            traza("getAll() devolvio", todas && todas.length);
            if (todas && todas.length) { return todas; }
        }

        var cuantas = (coleccion && typeof coleccion.getLength === "function")
            ? coleccion.getLength() : 0;
        var filas = [];
        for (var i = 0; i < cuantas; i++) {
            filas.push(coleccion.get(i));
        }
        traza("por indice se armaron", filas.length);
        return filas;
    }

    /* El estado de UNA fila. Cada paso se traza por separado para que, si devuelve
     * `undefined`, se vea EN CUAL paso se cortó y no haya que adivinarlo. */
    function estadoDeLaFila(fila) {
        traza("fila", claves(fila));

        var datos = fila && (fila.data || (typeof fila.getData === "function" ? fila.getData() : null));
        traza("data", claves(datos));

        var registro = datos && (datos.entity || (typeof datos.getEntity === "function" ? datos.getEntity() : null));
        traza("entity", claves(registro));

        if (registro && typeof registro.getId === "function") {
            traza("id de la fila", registro.getId());
        }

        /* Tres nombres para la misma coleccion segun version y tipo de grilla. La
         * documentacion solo bendice `columns`, y solo en grillas editables. */
        var columnas = null;
        if (registro) {
            if (typeof registro.getAttributes === "function") {
                columnas = registro.getAttributes();
                traza("via getAttributes()", claves(columnas));
            } else if (registro.attributes) {
                columnas = registro.attributes;
                traza("via .attributes", claves(columnas));
            } else if (registro.columns) {
                columnas = registro.columns;
                traza("via .columns", claves(columnas));
            } else {
                traza("NO HAY coleccion de columnas en la fila", FILA.columna);
            }
        }

        if (!columnas || typeof columnas.get !== "function") { return undefined; }

        var nombres = [];
        if (typeof columnas.forEach === "function") {
            columnas.forEach(function (c) { nombres.push(c && c.getName && c.getName()); });
        }
        traza("columnas disponibles", nombres.join(", "));

        var columna = columnas.get(FILA.columna);
        traza("columna " + FILA.columna, claves(columna));
        return (columna && typeof columna.getValue === "function") ? columna.getValue() : undefined;
    }

    function estadosSeleccionados(control) {
        try {
            traza("control recibido", claves(control));
            var grid = control.getGrid();
            var filas = filasDeLaGrilla(grid);
            var estados = [];
            for (var i = 0; i < filas.length; i++) {
                var estado = estadoDeLaFila(filas[i]);
                if (estado !== undefined && estado !== null) { estados.push(estado); }
            }
            traza("estados leidos", estados);
            return estados.length ? estados : null;
        } catch (e) {
            traza("EXCEPCION", e && e.message);
            return null;
        }
    }

    /*
     * `true` si AL MENOS UNA de las filas seleccionadas admite la accion.
     *
     * "Al menos una" y no "todas", a proposito: trabajar en lote es lo normal acá, y
     * exigir que las 100 esten en el estado justo obligaria a depurar la seleccion a
     * mano. Las que no correspondan las rechaza el plugin y el resumen final las
     * nombra una por una, que es informacion util, no ruido.
     *
     * Si no se pudo leer el estado, devuelve `true`: ocultar un boton que el usuario
     * necesita es peor que mostrarle uno que el servidor va a rechazar.
     */
    function algunaAdmite(accion, control) {
        traza("evaluando la regla de", accion);
        var estados = estadosSeleccionados(control);
        if (estados === null) {
            traza("sin estados → MUESTRA el boton de", accion);
            return true;
        }
        var validos = TRANSICIONES_VALIDAS[accion] || [];
        var resultado = estados.some(function (estado) { return validos.indexOf(estado) >= 0; });
        traza("accion " + accion + " · validos " + validos + " · estados " + estados + " → ", resultado);
        return resultado;
    }

    function cambioDe(config, valor) {
        var cambio = {};
        cambio[config.columna] = valor;
        return cambio;
    }

    /*
     * Abre el dialogo de motivo y devuelve el texto, o null si el usuario
     * cancelo.
     *
     * CREACION RAPIDA, no el formulario principal en un modal (corregido el
     * 2026-09-23). Antes se usaba `navigateTo` con `pageType: "entityrecord"`,
     * que mete el formulario PRINCIPAL completo dentro del dialogo: barra de
     * comandos (Guardar, Nuevo, Flujo), titulo de registro, pestaña y la barra
     * de Copilot. Para pedir una linea de texto.
     *
     * El motivo por el que se habia descartado la creacion rapida era que "solo
     * `entityrecord` devuelve valor". Eso vale contra una PAGINA CUSTOM, no
     * contra la creacion rapida: Learn dice textual que el callback de exito de
     * `openForm` "se ejecuta solo cuando se guarda un registro en un formulario
     * de creacion rapida abierto con openForm", y ese callback recibe
     * `savedEntityReference`.
     *
     * LO QUE SE PIERDE: `openForm` no admite un titulo propio, asi que el
     * contexto ("que accion, sobre cuantas filas") ya no va en el encabezado del
     * dialogo. El usuario acaba de apretar ese boton, y el resumen final vuelve
     * a nombrar la accion y la cantidad.
     *
     * LO QUE NO ESTA VERIFICADO: que hace el promise si el usuario CANCELA.
     * Learn solo documenta que el callback de exito corre al guardar. Por eso
     * hay un manejador de rechazo que devuelve null, y `pedirMotivo` se llama
     * ANTES de abrir cualquier indicador de progreso: si el promise no se
     * resolviera nunca, no queda nada bloqueando la pantalla.
     */
    function pedirMotivo() {
        return Xrm.Navigation.openForm({
            entityName: MOTIVO.tabla,
            useQuickCreateForm: true
        }).then(function (resultado) {
            var ref = resultado && resultado.savedEntityReference && resultado.savedEntityReference[0];
            if (!ref) {
                return null;   // cerro el dialogo sin guardar
            }
            return Xrm.WebApi.retrieveRecord(MOTIVO.tabla, ref.id, "?$select=" + MOTIVO.columna)
                .then(function (registro) {
                    var texto = registro[MOTIVO.columna];
                    // El registro es transporte: se borra. Que el borrado
                    // falle no invalida el motivo ya leido.
                    return Xrm.WebApi.deleteRecord(MOTIVO.tabla, ref.id).then(
                        function () { return texto; },
                        function () { return texto; }
                    );
                });
        }, function () {
            return null;   // cancelo, o el dialogo no se pudo abrir: no se toca nada
        });
    }

    /*
     * Igual que `ejecutar`, pero el texto lo pide el dialogo en vez de una
     * confirmacion. Sin motivo no se toca NADA.
     */
    function ejecutarConMotivo(nombreAccion, tabla, columnaMensaje, cambioBase, ids, control) {
        var t = idioma();
        if (!ids || !ids.length) {
            return Xrm.Navigation.openAlertDialog({ text: t.ninguna, confirmButtonLabel: t.cerrar });
        }
        var total = ids.length;
        return pedirMotivo().then(function (motivo) {
            if (!motivo) {
                return motivo === null
                    ? null
                    : Xrm.Navigation.openAlertDialog({ text: t.sinMotivo, confirmButtonLabel: t.cerrar });
            }
            var cambio = {};
            for (var clave in cambioBase) {
                if (Object.prototype.hasOwnProperty.call(cambioBase, clave)) {
                    cambio[clave] = cambioBase[clave];
                }
            }
            cambio[columnaMensaje] = motivo;
            return conProgreso(
                armar(t.progreso, { accion: nombreAccion, hechas: 0, n: total }),
                function () {
                    return aplicar(tabla, ids, cambio, function (hechas) {
                        mostrarProgreso(armar(t.progreso, { accion: nombreAccion, hechas: hechas, n: total }));
                    });
                }
            ).then(function (fallas) {
                refrescar(control);
                var ok = total - fallas.length;
                var texto = fallas.length
                    ? armar(t.conFallas, { ok: ok, n: total, mal: fallas.length }) + "\n\n" + fallas.join("\n")
                    : armar(t.listo, { ok: ok, n: total });
                return Xrm.Navigation.openAlertDialog({ text: texto, confirmButtonLabel: t.cerrar });
            });
        });
    }

    return {
        digitada: function (ids, control) {
            return ejecutar("Digitada", FILA.tabla, cambioDe(FILA, FILA.DIGITADA), ids, control);
        },
        aprobar: function (ids, control) {
            return ejecutar("Aprobar", FILA.tabla, cambioDe(FILA, FILA.APROBADA), ids, control);
        },
        atendido: function (ids, control) {
            return ejecutar("Atendido", SOLICITUD.tabla,
                cambioDe(SOLICITUD, SOLICITUD.CERRADA), ids, control);
        },
        descartar: function (ids, control) {
            return ejecutar("Descartar", SOLICITUD.tabla,
                cambioDe(SOLICITUD, SOLICITUD.DESCARTADA), ids, control);
        },

        // --- los cuatro que piden un texto ---
        rechazadaAs400: function (ids, control) {
            return ejecutarConMotivo("Rechazada en AS400", FILA.tabla, FILA.mensaje,
                cambioDe(FILA, FILA.RECHAZADA_AS400), ids, control);
        },
        anular: function (ids, control) {
            return ejecutarConMotivo("Anular", FILA.tabla, FILA.mensaje,
                cambioDe(FILA, FILA.ANULADA), ids, control);
        },
        devolver: function (ids, control) {
            // Devolver deja la fila otra vez en Validada, con el mensaje del
            // supervisor: es lo que la deja visible en "Devueltas".
            return ejecutarConMotivo("Devolver", FILA.tabla, FILA.mensaje,
                cambioDe(FILA, FILA.VALIDADA), ids, control);
        },
        revisado: function (ids, control) {
            /*
             * NO pide texto (corregido el 2026-09-23). Antes abria el dialogo de
             * motivo y escribia la nota en `sanic_motivorevision`. Dos problemas:
             *
             *  - la lista blanca no admite esa columna de una persona, asi que el
             *    boton fallaba SIEMPRE con "la(s) columna(s) sanic_motivorevision
             *    no esta(n) permitida(s)";
             *  - y esa columna no es del operador: la escriben los flujos para
             *    explicar POR QUE hace falta revisar ("Validacion fallida 3
             *    veces"). Es lo que el operador LEE. La nota lo habria pisado.
             *
             * Ahora solo apaga la marca. `RevisionAtendidaStep` toma el motivo que
             * ya estaba, lo deja en la Bitacora con quien y cuando, y limpia la
             * columna. Es lo que hace el mockup aprobado el 2026-09-20.
             */
            return ejecutar("Revisado", SOLICITUD.tabla,
                { sanic_requiererevision: false }, ids, control);
        },

        /*
         * --- las reglas del ribbon (EnableRule / CustomRule) ---
         *
         * En Unified Interface un comando DESHABILITADO NO SE VE (Learn, "Define
         * ribbon enable rules": "commands that are disabled are hidden"), asi que
         * devolver `false` aca es lo que hace desaparecer el boton.
         *
         * Las cuatro acciones sobre la Solicitud (atendido, descartar, revisado) no
         * llevan regla: su estado no esta en las mismas grillas y hoy no hay un caso
         * reportado. Cuando lo haya, se agregan igual que estas.
         */
        puedeDigitada: function (control) { return algunaAdmite("digitada", control); },
        puedeAprobar: function (control) { return algunaAdmite("aprobar", control); },
        puedeDevolver: function (control) { return algunaAdmite("devolver", control); },
        puedeRechazadaAs400: function (control) { return algunaAdmite("rechazadaas400", control); },
        puedeAnular: function (control) { return algunaAdmite("anular", control); }
    };
})();
