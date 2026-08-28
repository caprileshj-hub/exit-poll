# TM 2025: segunda auditoria de faltantes 06/22/23

Fecha de generacion: 2026-08-26T23:21:20.622907+00:00

## Metodologia

- Se parte del TM original `backend/tm_2025_macedonia_estandar.csv` de Asamblea Macedonia, no del candidato previo.
- Se restringe el universo a codigos de estado `06`, `22` y `23` dentro de `tm_2025_missing_centers_candidates.csv`.
- Para cada candidato se verifica presencia en Regionales 2025 por API/CSV previo y pagina publica; ausencia en Asamblea por TM reconstruido y URL directa esperable; y presencia historica en TM 2024, 2018 y 2015.
- `cantidadMesas=1` en Regionales se trata como evidencia fuerte de centro activo de una mesa. `cantidadMesas=0` no se convierte automaticamente en una mesa, aunque se reporte electorado.

## Validacion territorial de partida

| Estado | Esperado centros | TM Asamblea centros | Deficit centros | Esperado mesas | TM Asamblea mesas | Deficit mesas |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BOLIVAR | 817 | 812 | 5 | 1429 | 1424 | 5 |
| AMAZONAS | 150 | 148 | 2 | 192 | 190 | 2 |
| DELTA AMACURO | 195 | 194 | 1 | 237 | 236 | 1 |

## Resultado por estado

### BOLIVAR

- Candidatos auditados: 18.
- Clasificacion: {'INDETERMINADO': 10, 'CONFIRMADO': 8}.
- Deficit requerido: 817 - 812 = 5 centros; 5 mesas.
- Electores confirmados: 2042; confirmados+probables: 2042; brecha secundaria aproximada: 976.

### AMAZONAS

- Candidatos auditados: 5.
- Clasificacion: {'CONFIRMADO': 1, 'INDETERMINADO': 3, 'PROBABLE': 1}.
- Deficit requerido: 150 - 148 = 2 centros; 2 mesas.
- Electores confirmados: 489; confirmados+probables: 596; brecha secundaria aproximada: 612.

### DELTA AMACURO

- Candidatos auditados: 1.
- Clasificacion: {'PROBABLE': 1}.
- Deficit requerido: 195 - 194 = 1 centros; 1 mesas.
- Electores confirmados: 0; confirmados+probables: 467; brecha secundaria aproximada: 477.

## Candidatos evaluados

| Codigo | Estado | Municipio | Parroquia | Centro | Mesas 2025 | Electores 2025 | Clasificacion | Evidencia |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| 060102037 | BOLÍVAR | CARONI | ONCE DE ABRIL | UNIDAD EDUCATIVA COLEGIO LA PRADERA | 0 | 669 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f426346dcb5789292c5 hash 0e0f33cdf74a75d11d46553fb1f653870977d39039cf2e8fe92c4ec4bafa6703; HTML Regionales status 200 hash f02f4cdced18 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_caroni_once-de-abril_unidad-educativa-colegio-la-pradera__426a473f93abcbc0.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060103016 | BOLÍVAR | CARONI | VISTA AL SOL | UNIDAD EDUCATIVA COLEGIO ANDRES ELOY BLANCO | 1 | 271 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f426346dcb578929288 hash dde3c4300fba1242dd4af6a1113d32e54ac4cf0ef15275fd4a80a4af07df38e8; HTML Regionales status 200 hash 1898f4dd93b9 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_caroni_vista-al-sol_unidad-educativa-colegio-andres-eloy-blanco__c7a24b02d4fdb51b.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060105032 | BOLÍVAR | CARONI | DALLA COSTA | COLEGIO JUAN VICENTE GONZALEZ | 1 | 563 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f426346dcb5789293a8 hash c422734d7e33a91b38dc761b0b2b36c5850fa2fe201f20923ebbcd7ce8863383; HTML Regionales status 200 hash c3d3d2d4a58c cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_caroni_dalla-costa_colegio-juan-vicente-gonzalez__193cc7b53101f213.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060301020 | BOLÍVAR | ANGOSTURA DEL OR | CATEDRAL | ESCUELA ZEA | 1 | 767 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f426346dcb578929669 hash 861ac62ac88fe6006240fefa347a3726f1e9c0d8f6f5dbfb77d77e869f466d6a; HTML Regionales status 200 hash c497d539f45e cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_angostura-del-or_catedral_escuela-zea__b8f02ca9779ec3c7.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060307004 | BOLÍVAR | ANGOSTURA DEL OR | ORINOCO | UNIDA EDUCATIVA INTEGRAL BOLIVARIANA CURIAPO | 1 | 91 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929acd hash 62fb130d1392ae0464f383d7cf7a48c10863c79b35fbae874e308eb8032b2de3; HTML Regionales status 200 hash b3f2c7c94d90 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_angostura-del-or_orinoco_unida-educativa-integral-bolivariana-curiapo__fb1a99e3906a8892.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060403005 | BOLÍVAR | PIAR | PEDRO COVA | ESCUELA INTEGRAL BOLIVARIANA EL PLOMO | 0 | 195 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929b9c hash 4648c359dc569fcbc34ca2a49eb40afbfd9556f76207c2aa9c5d2bbdf760da6d; HTML Regionales status 200 hash d048a3315e3a cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_piar_pedro-cova_escuela-integral-bolivariana-el-plomo__1eefcb6f4c9458fd.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060602005 | BOLÍVAR | SUCRE | ARIPAO | UNIDAD EDUCATIVA BOLIVARIANA SANTA MARIA DE EREBATO | 0 | 298 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929c2c hash 156e6ca1254fb9024e500920d0b34e00888732b9abb016fa196dbb8535c8de41; HTML Regionales status 200 hash 73b124aa1009 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_sucre_aripao_unidad-educativa-bolivariana-santa-maria-de-erebato__ca5d0f3d0cdca6af.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060602006 | BOLÍVAR | SUCRE | ARIPAO | CAMPAMENTO ENTRERIOS | 0 | 282 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929c2c hash 156e6ca1254fb9024e500920d0b34e00888732b9abb016fa196dbb8535c8de41; HTML Regionales status 200 hash 3865d0541abf cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_sucre_aripao_campamento-entrerios__866f0c9ad94245e3.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060602009 | BOLÍVAR | SUCRE | ARIPAO | ESCUELA BOLIVARIANA SHIMARAÑA | 0 | 141 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929c2c hash 156e6ca1254fb9024e500920d0b34e00888732b9abb016fa196dbb8535c8de41; HTML Regionales status 200 hash 0159cc31ac21 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_sucre_aripao_escuela-bolivariana-shimarana__116a70e8a1ad327b.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060701010 | BOLÍVAR | SIFONTES | CM. TUMEREMO | ESCUELA NACIONAL SAN MARTIN DE TURUNBAN | 0 | 889 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929c5d hash 9b7ebd3cd729abdcf7a0a953ddb1767586404e744b776feb3997fb72d839fd4d; HTML Regionales status 200 hash 193f02a0346d cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_sifontes_cm-tumeremo_escuela-nacional-san-martin-de-turunban__2070c12db6928bbb.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060701012 | BOLÍVAR | SIFONTES | CM. TUMEREMO | ESCUELA UNITARIA ESPERANZA FE Y ALEGRIA | 0 | 315 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929c5d hash 9b7ebd3cd729abdcf7a0a953ddb1767586404e744b776feb3997fb72d839fd4d; HTML Regionales status 200 hash db2828a5bead cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_sifontes_cm-tumeremo_escuela-unitaria-esperanza-fe-y-alegria__41033f6bbd614c7e.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060701013 | BOLÍVAR | SIFONTES | CM. TUMEREMO | ESCUELA BASICA NACIONAL UNITARIA SAN JUAN DE VENAMO | 0 | 111 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929c5d hash 9b7ebd3cd729abdcf7a0a953ddb1767586404e744b776feb3997fb72d839fd4d; HTML Regionales status 200 hash 25a0d0aea8e3 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_sifontes_cm-tumeremo_escuela-basica-nacional-unitaria-san-juan-de-venamo__17ec54db310b8cad.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060801014 | BOLÍVAR | BLVNO DE ANGOSTU | CM. CIUDAD PIAR | UNIDAD EDUCATIVA NACIONAL ANDRES BELLO | 1 | 115 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929cd5 hash 45b363906a33fd21b230e170581da80c3a132612e9a3e163a6ade5a86e020603; HTML Regionales status 200 hash d451dea6eec1 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_blvno-de-angostu_cm-ciudad-piar_unidad-educativa-nacional-andres-bello__fcb7b1c243e6c1fc.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060802002 | BOLÍVAR | BLVNO DE ANGOSTU | SAN FRANCISCO | COLEGIO SAN JUAN BAUTISTA | 1 | 72 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929cfe hash 9ad498b7042ec5b6fb653faa665c8e61f3c5be6f7aee66a24453f6de56ef22c3; HTML Regionales status 200 hash 1740cf74a639 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_blvno-de-angostu_san-francisco_colegio-san-juan-bautista__12f21c8c712c5c0f.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060802006 | BOLÍVAR | BLVNO DE ANGOSTU | SAN FRANCISCO | ESCUELA BASICA UNITARIA JUAS JUAL 1 | 1 | 92 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929cfe hash 9ad498b7042ec5b6fb653faa665c8e61f3c5be6f7aee66a24453f6de56ef22c3; HTML Regionales status 200 hash 0e73043c46f1 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_blvno-de-angostu_san-francisco_escuela-basica-unitaria-juas-jual-1__63505d6a4bad1536.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060802011 | BOLÍVAR | BLVNO DE ANGOSTU | SAN FRANCISCO | ESCUELA BASICA NACIONAL UNITARIA LOS MONOS NUCLEO ESCOLAR RURAL 188 | 1 | 71 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929cfe hash 9ad498b7042ec5b6fb653faa665c8e61f3c5be6f7aee66a24453f6de56ef22c3; HTML Regionales status 200 hash 9ad2d6ae1a85 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_blvno-de-angostu_san-francisco_escuela-basica-nacional-unitaria-los-monos-nucleo-escolar-rural-188__5e9c0e2b7df450c6.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060803009 | BOLÍVAR | BLVNO DE ANGOSTU | BARCELONETA | ESCUELA BASICA NACIONAL BOLIVARIANA LAS BONITAS | 0 | 167 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929d18 hash 6ec6f084ff4526b2e8537e0f9db3405dc9831e9c6766268415a0d6218e863ddb; HTML Regionales status 200 hash 0051cedfe3d2 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_blvno-de-angostu_barceloneta_escuela-basica-nacional-bolivariana-las-bonitas__e3d29dad2e1f4d07.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 060803010 | BOLÍVAR | BLVNO DE ANGOSTU | BARCELONETA | CENTRO DE EDUCACIÒN INTEGRAL BOLIVARIANO CAMPO GRANDE. EL CHIGUAO | 0 | 89 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f436346dcb578929d18 hash 6ec6f084ff4526b2e8537e0f9db3405dc9831e9c6766268415a0d6218e863ddb; HTML Regionales status 200 hash af3584b4b8f1 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_bolivar_blvno-de-angostu_barceloneta_centro-de-educacion-integral-bolivariano-campo-grande-el-chiguao__3d48990a122d49a0.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 220101023 | AMAZONAS | ATURES | FERNANDO GIRON TOVAR | CENTRO EDUCATIVO INTEGRAL BOLIVARIANO RIO VENTUARI | 1 | 489 | CONFIRMADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f506346dcb578935659 hash 4472c71194c515ecfdd4ca4a11aa82566f906b61d14d9b4036a42bc89305a03c; HTML Regionales status 200 hash 1dcc446fe7f4 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_amazonas_atures_fernando-giron-tovar_centro-educativo-integral-bolivariano-rio-ventuari__b07e5a8fcb71a137.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 220402001 | AMAZONAS | RIO NEGRO | SOLANO | ESCUELA BASICA ROMULO GALLEGOS | 0 | 258 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f536346dcb578938fd1 hash 54c3989b56b869f6c97939090177fad0626cd14ccbd7a35cdc61f59e6306933e; HTML Regionales status 200 hash 31eeb2a4dbf5 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_amazonas_rio-negro_solano_escuela-basica-romulo-gallegos__0e100e83e926866a.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 220404002 | AMAZONAS | RIO NEGRO | COCUY | UNIDAD EDUCATIVA EL COCUY | 0 | 184 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f536346dcb578938fe2 hash c3b2494af83312de9e44bffbf9bb511c7b4efc3b363865f23c577a26434cbfb3; HTML Regionales status 200 hash 1cdba487a26a cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_amazonas_rio-negro_cocuy_unidad-educativa-el-cocuy__29fa21980498d895.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 220602004 | AMAZONAS | MANAPIARE | ALTO VENTUARI | CENTRO MOVIL CAÑO IGUANA | 0 | 107 | PROBABLE | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f536346dcb578939045 hash 5fef4f7a78368f0c021f0012c7089f30062ebb14274541578e1eca940649cd35; HTML Regionales status 200 hash 14bd8e9d0c71 cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_amazonas_manapiare_alto-ventuari_centro-movil-cano-iguana__e8c44fa1d1f8fc7b.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 220704002 | AMAZONAS | ALTO ORINOCO | MAVACA | UNIDAD EDUCATIVA YANOMAMI I | 0 | 513 | INDETERMINADO | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f536346dcb578939092 hash 97eb0bd3e699d20f6102c07fe9c3ce30c86ee164855baa3b3f88e6ec84e21537; HTML Regionales status 200 hash dd97c9b5f57a cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_amazonas_alto-orinoco_mavaca_unidad-educativa-yanomami-i__c328860196ecedc8.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |
| 230303004 | DELTA AMACURO | ANTONIO DIAZ | MANUEL RENAUD | E.B.NTRA. SRA DE LA CONSOLATA - ARAGUABISI | 0 | 467 | PROBABLE | Regionales API https://regionales.macedoniadelnorte.com/api/centros?parroquiaId=681f4f536346dcb57893915c hash 2b22131e3207f3e7f424a4b91baf52f8dfb92af66eaa4716284c639363e9c8ab; HTML Regionales status 200 hash 477af7b4ef3c cache backend/data/2025/regionales_candidate_pages_cache/regionales.macedoniadelnorte.com_delta-amacuro_antonio-diaz_manuel-renaud_ebntra-sra-de-la-consolata-araguabisi__7e73c295d4e531af.html; Asamblea URL status 404; codigo en TM Asamblea reconstruido: no. |

## Decision sobre TM v2

No se genero `backend/tm_2025_macedonia_estandar_candidate_completed_v2.csv`.

Razon: la evidencia documental no identifica de forma unica los 5 centros de Bolivar. Hay 8 candidatos con `cantidadMesas=1` en Regionales para un deficit de 5; varias combinaciones pueden acercarse a la brecha secundaria de electores, pero eso seria una seleccion aritmetica, no documental. Amazonas y Delta tambien contienen candidatos con electores y `cantidadMesas=0`, que quedan como probables/indeterminados segun el caso.

## Decision metodologica final

El TM 2025 aceptado para carga manual sigue siendo
`backend/tm_2025_macedonia_estandar.csv`: 15,728 centros, 27,705 mesas y
21,286,719 electores.

La brecha conocida queda preservada: 8 centros, 8 mesas y 2,126 electores
comparables contra el universo parlamentario fisico de 24 estados. No se imputa
porque no existe correspondencia documental unica suficiente para seleccionar
5+2+1 sin introducir una regla heuristica.

`230303004` queda como PROBABLE fuerte para Delta Amacuro, pero no confirmado:
Regionales renderiza el centro y reporta 467 electores; Asamblea responde 404;
aparece historicamente; el deficit de Delta esta localizado en Antonio Diaz. El
campo `cantidadMesas=0` impide convertirlo documentalmente en la mesa faltante
sin una regla adicional.

`060701010` queda registrado como falsador nominado de la afirmacion absoluta
"todos los missing units tienen menos de 800 electores": Regionales reporta 889
electores, aunque el centro sigue INDETERMINADO por `cantidadMesas=0`.
