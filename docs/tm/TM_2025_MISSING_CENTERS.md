# TM 2025: centros faltantes candidatos

Fecha de generacion: 2026-08-26T23:09:20.731352+00:00

## Estado del artefacto

**REJECTED AUDIT ARTIFACT - DO NOT IMPORT**

La version candidata `backend/tm_2025_macedonia_estandar_candidate_completed.csv`
se conserva como evidencia de auditoria, pero no debe usarse operacionalmente.
El filtro usado en esta pasada logro cuadrar el agregado nacional (15,736
centros y 27,713 mesas), pero agrego centros en Guarico, Lara, Merida, Miranda,
Nueva Esparta y Tachira. La segunda reconciliacion territorial ubico los
deficits reales en Bolivar (+5), Amazonas (+2) y Delta Amacuro (+1). Por tanto,
hacer coincidir el agregado nacional empeoro la reconciliacion territorial.

## Validacion de marco

- CNE operacional esperado: 15,736 centros y 27,713 mesas.
- TM Macedonia Asamblea actual: 15,728 centros y 27,705 mesas.
- Inventario Regionales Macedonia rastreado: 15,800 centros.
- Diferencia Regionales menos Asamblea: 104 centros candidatos.
- Candidatos recuperables documentalmente por API Regionales: 62 centros y 98 mesas.
- Subconjunto incluido en TM candidato exacto: 8 centros y 8 mesas.
- TM candidato separado: 15,736 centros, 27,713 mesas, 21,288,532 electores.
- Electores Asamblea actual: 21,286,719; electores agregados por el subconjunto incluido: 1,813.

## Criterio de inclusion

El cruce bruto Regionales 2025 menos Asamblea 2025 produce 104 codigos, no 8. Por tanto, Regionales no funciona como simple lista `Asamblea + faltantes`.

Para construir una version candidata separada que respete la brecha operacional nacional, se incluye solo el subconjunto que cumple simultaneamente: presente en Regionales 2025, ausente en Asamblea 2025, `cantidadMesas=1`, aparece en los dos TM 2024 locales y no aparece en TM 2018 ni TM 2015. Ese filtro produce exactamente 8 centros y 8 mesas. Se reportan los 104 en el CSV para auditoria.

## Evidencia por centro

| Codigo | Incluido | Estado | Municipio | Parroquia | Centro | Mesas | Electores | Historico | Fuente |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| 010114022 | no | DISTRITO CAPITAL | BLVNO LIBERTADOR | EL VALLE | ESCUELA BÁSICA DOCTOR ENRIQUE DELGADO PALACIOS | 3 | 2622 | 2024v2, 2024, 2015 | https://regionales.macedoniadelnorte.com/distrito-capital/blvno-libertador/el-valle/escuela-basica-doctor-enrique-delgado-palacios |
| 010114071 | no | DISTRITO CAPITAL | BLVNO LIBERTADOR | EL VALLE | IGLESIA EVANGELICA PENTESCOTAL BENDICION RECIBIDA | 0 | 334 | 2024v2 | https://regionales.macedoniadelnorte.com/distrito-capital/blvno-libertador/el-valle/iglesia-evangelica-pentescotal-bendicion-recibida |
| 010120047 | no | DISTRITO CAPITAL | BLVNO LIBERTADOR | SAN PEDRO | ESCUELA NACIONAL BOLIVARIANA ALI PRIMERA | 0 | 3937 | 2024v2 | https://regionales.macedoniadelnorte.com/distrito-capital/blvno-libertador/san-pedro/escuela-nacional-bolivariana-ali-primera |
| 020601037 | no | ANZOATEGUI | FREITES | CM. CANTAURA | ESCUELA UNITARIA EL MEREY | 0 | 134 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/anzoategui/freites/cm-cantaura/escuela-unitaria-el-merey |
| 020902002 | no | ANZOATEGUI | MIRANDA | ATAPIRIRE | ESCUELA BASICA SAN SIMON | 1 | 249 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/anzoategui/miranda/atapirire/escuela-basica-san-simon |
| 021002002 | no | ANZOATEGUI | MONAGAS | PIAR | ESCUELA ESTADAL SIN NUMERO | 0 | 115 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/anzoategui/monagas/piar/escuela-estadal-sin-numero |
| 021006002 | no | ANZOATEGUI | MONAGAS | ZUATA | ESCUELA UNITARIA LA MUCHACHA | 0 | 138 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/anzoategui/monagas/zuata/escuela-unitaria-la-muchacha |
| 021501016 | no | ANZOATEGUI | GUANTA | GUANTA | UNIDAD EDUCATIVA CIUDAD DE GUANTA | 3 | 2152 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/anzoategui/guanta/guanta/unidad-educativa-ciudad-de-guanta |
| 021601004 | no | ANZOATEGUI | PIRITU | PIRITU | ESCUELA BOLIVARIANA EL MEREY | 1 | 760 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/anzoategui/piritu/piritu/escuela-bolivariana-el-merey |
| 021601010 | no | ANZOATEGUI | PIRITU | PIRITU | CENTRO DE EDUCACION INICIAL PEDRO CELESTINO MUÑOZ | 2 | 1955 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/anzoategui/piritu/piritu/centro-de-educacion-inicial-pedro-celestino-munoz |
| 050103015 | no | BARINAS | ARISMENDI | LA UNION | CASA DE REFUGIO ANA HERRERA | 0 | 399 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/barinas/arismendi/la-union/casa-de-refugio-ana-herrera |
| 060102037 | no | BOLÍVAR | CARONI | ONCE DE ABRIL | UNIDAD EDUCATIVA COLEGIO LA PRADERA | 0 | 669 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/caroni/once-de-abril/unidad-educativa-colegio-la-pradera |
| 060103016 | no | BOLÍVAR | CARONI | VISTA AL SOL | UNIDAD EDUCATIVA COLEGIO ANDRES ELOY BLANCO | 1 | 271 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/caroni/vista-al-sol/unidad-educativa-colegio-andres-eloy-blanco |
| 060105032 | no | BOLÍVAR | CARONI | DALLA COSTA | COLEGIO JUAN VICENTE GONZALEZ | 1 | 563 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/caroni/dalla-costa/colegio-juan-vicente-gonzalez |
| 060301020 | no | BOLÍVAR | ANGOSTURA DEL OR | CATEDRAL | ESCUELA ZEA | 1 | 767 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/angostura-del-or/catedral/escuela-zea |
| 060307004 | no | BOLÍVAR | ANGOSTURA DEL OR | ORINOCO | UNIDA EDUCATIVA INTEGRAL BOLIVARIANA CURIAPO | 1 | 91 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/angostura-del-or/orinoco/unida-educativa-integral-bolivariana-curiapo |
| 060403005 | no | BOLÍVAR | PIAR | PEDRO COVA | ESCUELA INTEGRAL BOLIVARIANA EL PLOMO | 0 | 195 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/piar/pedro-cova/escuela-integral-bolivariana-el-plomo |
| 060602005 | no | BOLÍVAR | SUCRE | ARIPAO | UNIDAD EDUCATIVA BOLIVARIANA SANTA MARIA DE EREBATO | 0 | 298 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/sucre/aripao/unidad-educativa-bolivariana-santa-maria-de-erebato |
| 060602006 | no | BOLÍVAR | SUCRE | ARIPAO | CAMPAMENTO ENTRERIOS | 0 | 282 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/sucre/aripao/campamento-entrerios |
| 060602009 | no | BOLÍVAR | SUCRE | ARIPAO | ESCUELA BOLIVARIANA SHIMARAÑA | 0 | 141 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/sucre/aripao/escuela-bolivariana-shimarana |
| 060701010 | no | BOLÍVAR | SIFONTES | CM. TUMEREMO | ESCUELA NACIONAL SAN MARTIN DE TURUNBAN | 0 | 889 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/sifontes/cm-tumeremo/escuela-nacional-san-martin-de-turunban |
| 060701012 | no | BOLÍVAR | SIFONTES | CM. TUMEREMO | ESCUELA UNITARIA ESPERANZA FE Y ALEGRIA | 0 | 315 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/sifontes/cm-tumeremo/escuela-unitaria-esperanza-fe-y-alegria |
| 060701013 | no | BOLÍVAR | SIFONTES | CM. TUMEREMO | ESCUELA BASICA NACIONAL UNITARIA SAN JUAN DE VENAMO | 0 | 111 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/sifontes/cm-tumeremo/escuela-basica-nacional-unitaria-san-juan-de-venamo |
| 060801014 | no | BOLÍVAR | BLVNO DE ANGOSTU | CM. CIUDAD PIAR | UNIDAD EDUCATIVA NACIONAL ANDRES BELLO | 1 | 115 | 2024v2 | https://regionales.macedoniadelnorte.com/bolivar/blvno-de-angostu/cm-ciudad-piar/unidad-educativa-nacional-andres-bello |
| 060802002 | no | BOLÍVAR | BLVNO DE ANGOSTU | SAN FRANCISCO | COLEGIO SAN JUAN BAUTISTA | 1 | 72 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/blvno-de-angostu/san-francisco/colegio-san-juan-bautista |
| 060802006 | no | BOLÍVAR | BLVNO DE ANGOSTU | SAN FRANCISCO | ESCUELA BASICA UNITARIA JUAS JUAL 1 | 1 | 92 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/blvno-de-angostu/san-francisco/escuela-basica-unitaria-juas-jual-1 |
| 060802011 | no | BOLÍVAR | BLVNO DE ANGOSTU | SAN FRANCISCO | ESCUELA BASICA NACIONAL UNITARIA LOS MONOS NUCLEO ESCOLAR RURAL 188 | 1 | 71 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/blvno-de-angostu/san-francisco/escuela-basica-nacional-unitaria-los-monos-nucleo-escolar-rural-188 |
| 060803009 | no | BOLÍVAR | BLVNO DE ANGOSTU | BARCELONETA | ESCUELA BASICA NACIONAL BOLIVARIANA LAS BONITAS | 0 | 167 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/blvno-de-angostu/barceloneta/escuela-basica-nacional-bolivariana-las-bonitas |
| 060803010 | no | BOLÍVAR | BLVNO DE ANGOSTU | BARCELONETA | CENTRO DE EDUCACIÒN INTEGRAL BOLIVARIANO CAMPO GRANDE. EL CHIGUAO | 0 | 89 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/bolivar/blvno-de-angostu/barceloneta/centro-de-educacion-integral-bolivariano-campo-grande-el-chiguao |
| 070201014 | no | CARABOBO | CARLOS ARVELO | GUIGUE | CENTRO DE EDUCACION INICIAL NACIONAL BOLIVARIANO TENIENTE PEDRO CAMEJO | 4 | 4479 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/carabobo/carlos-arvelo/guigue/centro-de-educacion-inicial-nacional-bolivariano-teniente-pedro-camejo |
| 070302017 | no | CARABOBO | DIEGO IBARRA | AGUAS CALIENTES | ESCUELA BASICA BOLIVARIANA. PADRE DEHON | 0 | 1401 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/carabobo/diego-ibarra/aguas-calientes/escuela-basica-bolivariana-padre-dehon |
| 070601030 | no | CARABOBO | JUAN JOSE MORA | MORON | UNIDAD EDUCATIVA PRIVADA EDUARDO BLANCO | 0 | 1040 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/carabobo/juan-jose-mora/moron/unidad-educativa-privada-eduardo-blanco |
| 070904066 | no | CARABOBO | VALENCIA | MIGUEL PEÑA | COLEGIO RAMON IGNACIO MENDEZ (UNIDAD EDUCATIVA ANEXO BELLA VISTA) | 0 | 2266 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/carabobo/valencia/miguel-pena/colegio-ramon-ignacio-mendez-unidad-educativa-anexo-bella-vista |
| 080101007 | no | COJEDES | ANZOATEGUI | COJEDES | CENTRO DE EDUCACION INICIAL LOS MANGOS | 1 | 476 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/cojedes/anzoategui/cojedes/centro-de-educacion-inicial-los-mangos |
| 090101002 | no | FALCON | ACOSTA | SAN JUAN DE LOS CAYOS | ESCUELA BASICA BOLIVARIANA LOS TAPAROS | 1 | 422 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/falcon/acosta/san-juan-de-los-cayos/escuela-basica-bolivariana-los-taparos |
| 090103007 | no | FALCON | ACOSTA | LA PASTORA | ESCUELA BASICA VIENTO SUAVE | 1 | 165 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/falcon/acosta/la-pastora/escuela-basica-viento-suave |
| 091002024 | no | FALCON | MIRANDA | SAN GABRIEL | AMBULATORIO ANGEL PAYO PETIT | 2 | 1551 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/falcon/miranda/san-gabriel/ambulatorio-angel-payo-petit |
| 091002025 | no | FALCON | MIRANDA | SAN GABRIEL | AMBULATORIO TIPO I SAN JUAN BOSCO | 1 | 882 | 2024v2 | https://regionales.macedoniadelnorte.com/falcon/miranda/san-gabriel/ambulatorio-tipo-i-san-juan-bosco |
| 100401036 | no | GUARICO | MONAGAS | ALTAGRACIA DE ORITUCO | CENTRO DE VOTACION EL BANCO DE GUANAPE | 1 | 265 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/guarico/monagas/altagracia-de-orituco/centro-de-votacion-el-banco-de-guanape |
| 100901018 | si | GUARICO | S JOSE DE GUARIBE | SAN JOSE DE GUARIBE | CDCE NRO 11 | 1 | 178 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/guarico/s-jose-de-guaribe/san-jose-de-guaribe/cdce-nro-11 |
| 101501013 | no | GUARICO | SAN GERONIMO DE G | GUAYABAL | EPB NEGRA MATEA | 0 | 248 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/guarico/san-geronimo-de-g/guayabal/epb-negra-matea |
| 101502009 | no | GUARICO | SAN GERONIMO DE G | CAZORLA | ESCUELA PRIMARIA ESTADAL EL ZORRO | 1 | 81 | 2024v2 | https://regionales.macedoniadelnorte.com/guarico/san-geronimo-de-g/cazorla/escuela-primaria-estadal-el-zorro |
| 110502035 | no | LARA | PALAVECINO | JOSE G. BASTIDAS | CENTRO DE PARTICIPACION LAS AXAGUAS 2 VALLE LINDO | 0 | 703 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/lara/palavecino/jose-g-bastidas/centro-de-participacion-las-axaguas-2-valle-lindo |
| 110503006 | no | LARA | PALAVECINO | AGUA VIVA | CASA COMUNAL DE VALLECITO | 2 | 1089 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/lara/palavecino/agua-viva/casa-comunal-de-vallecito |
| 110801049 | si | LARA | ANDRES E BLANCO | PIO TAMAYO | MODULO DE ATENCION A NIÑOS | 1 | 222 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/lara/andres-e-blanco/pio-tamayo/modulo-de-atencion-a-ninos |
| 120307002 | no | MÉRIDA | ARZOBISPO CHACON | MUCUCHACHI | ESCUELA BASICA AGUA BLANCA | 1 | 70 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/merida/arzobispo-chacon/mucuchachi/escuela-basica-agua-blanca |
| 121802011 | si | MÉRIDA | SUCRE | CHIGUARA | EL PEDREGAL | 1 | 155 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/merida/sucre/chiguara/el-pedregal |
| 130203001 | no | MIRANDA | BRION | TACARIGUA | UNIDAD EDUCATIVA BARLOVENTO | 4 | 3357 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/brion/tacarigua/unidad-educativa-barlovento |
| 130203010 | no | MIRANDA | BRION | TACARIGUA | SALON DE COSTURA LAS CORALIA | 0 | 470 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/brion/tacarigua/salon-de-costura-las-coralia |
| 130301013 | no | MIRANDA | GUAICAIPURO | LOS TEQUES | COLEGIO NUESTRA SEÑORA DE FATIMA | 3 | 2816 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/guaicaipuro/los-teques/colegio-nuestra-senora-de-fatima |
| 130301092 | no | MIRANDA | GUAICAIPURO | LOS TEQUES | CASA COMUNAL EL TRIGO | 0 | 184 | 2024v2 | https://regionales.macedoniadelnorte.com/miranda/guaicaipuro/los-teques/casa-comunal-el-trigo |
| 130401004 | no | MIRANDA | INDEPENDENCIA | STA TERESA DEL TUY | UNIDAD EDUCATIVA PRIVADA FRANCISCO LINARES ALCANTARA | 1 | 955 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/independencia/sta-teresa-del-tuy/unidad-educativa-privada-francisco-linares-alcantara |
| 130401038 | no | MIRANDA | INDEPENDENCIA | STA TERESA DEL TUY | CENTRO DE EDUCACION INICIAL CIUDAD LOZADA | 0 | 181 | 2024v2 | https://regionales.macedoniadelnorte.com/miranda/independencia/sta-teresa-del-tuy/centro-de-educacion-inicial-ciudad-lozada |
| 130401046 | si | MIRANDA | INDEPENDENCIA | STA TERESA DEL TUY | CASA COMUNAL HÉROES DE LA FE | 1 | 128 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/miranda/independencia/sta-teresa-del-tuy/casa-comunal-heroes-de-la-fe |
| 130801069 | no | MIRANDA | PLAZA | GUARENAS | ESCUELA RURAL BOLIVARIANA CAMPO ALEGRE 028 | 0 | 79 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/plaza/guarenas/escuela-rural-bolivariana-campo-alegre-028 |
| 130801082 | no | MIRANDA | PLAZA | GUARENAS | EBE CREACION ZUMBA | 0 | 470 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/plaza/guarenas/ebe-creacion-zumba |
| 130901028 | no | MIRANDA | SUCRE | PETARE | COLEGIO NUESTRA SEÑORA DE LA GUIA | 2 | 1657 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/sucre/petare/colegio-nuestra-senora-de-la-guia |
| 130901032 | no | MIRANDA | SUCRE | PETARE | UNIDAD EDUCATIVA PREESCOLAR AMALIVAC | 0 | 1001 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/sucre/petare/unidad-educativa-preescolar-amalivac |
| 130901161 | no | MIRANDA | SUCRE | PETARE | CENTRO DE ORIENTACION FAMILIAR ANA SOTO | 0 | 228 | 2024v2 | https://regionales.macedoniadelnorte.com/miranda/sucre/petare/centro-de-orientacion-familiar-ana-soto |
| 131002030 | no | MIRANDA | URDANETA | NUEVA CUA | CASA COMUNAL (SECTOR FUNDAESTE) | 0 | 253 | 2024v2 | https://regionales.macedoniadelnorte.com/miranda/urdaneta/nueva-cua/casa-comunal-sector-fundaeste |
| 131202010 | no | MIRANDA | CRISTOBAL ROJAS | LAS BRISAS | UNIDAD EDUCATIVA ESTADAL ANDRES ELOY BLANCO | 0 | 17 | 2024v2 | https://regionales.macedoniadelnorte.com/miranda/cristobal-rojas/las-brisas/unidad-educativa-estadal-andres-eloy-blanco |
| 131301005 | no | MIRANDA | LOS SALIAS | SAN ANTONIO LOS ALTOS | UNIDAD EDUCATIVA LOS CASTORES | 4 | 3163 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/miranda/los-salias/san-antonio-los-altos/unidad-educativa-los-castores |
| 131701022 | si | MIRANDA | CARRIZAL | CARRIZAL | UNIDAD EDUCATIVA JOSE MARIA VARGAS | 1 | 553 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/miranda/carrizal/carrizal/unidad-educativa-jose-maria-vargas |
| 140708035 | no | MONAGAS | MATURIN | LAS COCUIZAS | CASA DE ABRIGO JOSE MERCEDES SANTELIZ | 1 | 797 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/monagas/maturin/las-cocuizas/casa-de-abrigo-jose-mercedes-santeliz |
| 141301009 | no | MONAGAS | URACOA | CM. URACOA | ESCUELA UNITARIA NUMERO 315 | 1 | 370 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/monagas/uracoa/cm-uracoa/escuela-unitaria-numero-315 |
| 150401011 | no | NUEVA ESPARTA | MANEIRO | CM. PAMPATAR | FUNDACION CULTURAL ALI PRIMERA | 2 | 1566 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/nueva-esparta/maneiro/cm-pampatar/fundacion-cultural-ali-primera |
| 150401013 | no | NUEVA ESPARTA | MANEIRO | CM. PAMPATAR | CENTRO DE EDUCACION INICIAL SIMONCITO ANA CLETA LABORI | 0 | 236 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/nueva-esparta/maneiro/cm-pampatar/centro-de-educacion-inicial-simoncito-ana-cleta-labori |
| 150601012 | no | NUEVA ESPARTA | MARI�O | CM. PORLAMAR | UNIDAD EDUCATIVA NUESTRA SEÑORA DE COROMOTO | 2 | 1819 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/nueva-esparta/mario/cm-porlamar/unidad-educativa-nuestra-senora-de-coromoto |
| 150601033 | no | NUEVA ESPARTA | MARI�O | CM. PORLAMAR | UNIDAD EDUCATIVA DON ROMULO GALLEGOS | 1 | 556 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/nueva-esparta/mario/cm-porlamar/unidad-educativa-don-romulo-gallegos |
| 150601034 | no | NUEVA ESPARTA | MARI�O | CM. PORLAMAR | UNIDAD EDUCATIVA EDUCACIONAL PORLAMAR | 2 | 1471 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/nueva-esparta/mario/cm-porlamar/unidad-educativa-educacional-porlamar |
| 150601038 | no | NUEVA ESPARTA | MARI�O | CM. PORLAMAR | UNIDAD EDUCATIVA INSTITUTO EDUCATIVO NUEVA ESPARTA | 1 | 744 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/nueva-esparta/mario/cm-porlamar/unidad-educativa-instituto-educativo-nueva-esparta |
| 150702016 | si | NUEVA ESPARTA | PENIN. DE MACANAO | SAN FRANCISCO | ANTIGUO MERCALITO ROBLEDAL | 1 | 277 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/nueva-esparta/penin-de-macanao/san-francisco/antiguo-mercalito-robledal |
| 150901016 | no | NUEVA ESPARTA | TUBORES | CM. PUNTA DE PIEDRAS | STADIUM JOSE JESUS GOMEZ IBARRA | 1 | 269 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/nueva-esparta/tubores/cm-punta-de-piedras/stadium-jose-jesus-gomez-ibarra |
| 150901019 | no | NUEVA ESPARTA | TUBORES | CM. PUNTA DE PIEDRAS | UNIDAD EDUCATIVA SAN MIGUEL ARCANGEL | 0 | 1883 | 2024v2 | https://regionales.macedoniadelnorte.com/nueva-esparta/tubores/cm-punta-de-piedras/unidad-educativa-san-miguel-arcangel |
| 150901023 | si | NUEVA ESPARTA | TUBORES | CM. PUNTA DE PIEDRAS | EMBARCADERO NAVAL EL INDIO | 1 | 119 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/nueva-esparta/tubores/cm-punta-de-piedras/embarcadero-naval-el-indio |
| 160801013 | no | PORTUGUESA | TUREN | CM. VILLA BRUZUAL | CENTRO DE CAPACITACION EN ARTES Y OFICIO AMALIA MORANDI | 1 | 1103 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/portuguesa/turen/cm-villa-bruzual/centro-de-capacitacion-en-artes-y-oficio-amalia-morandi |
| 170302009 | no | SUCRE | BERMUDEZ | SANTA ROSA | UNIDAD GERONTOLOGICA JOSE MANUEL ZUNIAGA. | 2 | 1380 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/sucre/bermudez/santa-rosa/unidad-gerontologica-jose-manuel-zuniaga |
| 170706001 | no | SUCRE | MONTES | SAN LORENZO | ESCUELA CONCENTRADA RURAL BOLIVARIANA LAS TRINCHERAS | 1 | 363 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/sucre/montes/san-lorenzo/escuela-concentrada-rural-bolivariana-las-trincheras |
| 170706003 | no | SUCRE | MONTES | SAN LORENZO | ESCUELA BOLIVARIANA LA FRAGUA | 1 | 224 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/sucre/montes/san-lorenzo/escuela-bolivariana-la-fragua |
| 170902002 | no | SUCRE | SUCRE | AYACUCHO | UNIVERSIDAD EXPERIMENTAL DE LA FUERZA ARMADA | 1 | 687 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/sucre/sucre/ayacucho/universidad-experimental-de-la-fuerza-armada |
| 170902003 | no | SUCRE | SUCRE | AYACUCHO | ASILO DE ANCIANOS SAN VICENTE DE PAUL | 0 | 840 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/sucre/sucre/ayacucho/asilo-de-ancianos-san-vicente-de-paul |
| 180101009 | no | TÁCHIRA | AYACUCHO | CM. COLON | UNIDAD EDUCATIVA ESTADAL ANDRES BELLO | 3 | 2334 | 2024v2, 2024, 2015 | https://regionales.macedoniadelnorte.com/tachira/ayacucho/cm-colon/unidad-educativa-estadal-andres-bello |
| 180103004 | no | TÁCHIRA | AYACUCHO | SAN PEDRO DEL RIO | ESCUELA BOLIVARIANA S/N NER 358 SECTOR LA LAJA | 1 | 119 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/tachira/ayacucho/san-pedro-del-rio/escuela-bolivariana-sn-ner-358-sector-la-laja |
| 180301014 | no | TÁCHIRA | CAPACHO NUEVO | CM. CAPACHO NUEVO | ESCUELA DE LABORES NOCTURNA INDEPENDENCIA | 1 | 432 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/tachira/capacho-nuevo/cm-capacho-nuevo/escuela-de-labores-nocturna-independencia |
| 180302009 | si | TÁCHIRA | CAPACHO NUEVO | JUAN GERMAN ROSCIO | CLUB SOCIAL PAN DE AZUCAR | 1 | 181 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/tachira/capacho-nuevo/juan-german-roscio/club-social-pan-de-azucar |
| 180402011 | no | TÁCHIRA | CARDENAS | LA FLORIDA | ESCUELA CONCENTRADA MIXTA NACIONAL NÚMERO 2635 | 0 | 59 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/tachira/cardenas/la-florida/escuela-concentrada-mixta-nacional-numero-2635 |
| 180801022 | no | TÁCHIRA | SAN CRISTOBAL | LA CONCORDIA | ESCUELA ESTADAL UNITARIA 199 | 1 | 238 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/tachira/san-cristobal/la-concordia/escuela-estadal-unitaria-199 |
| 180901008 | no | TÁCHIRA | URIBANTE | CM. PREGONERO | ESCUELA BOLIVARIANA ANA YSABEL CONTRERAS DE BELANDRIA AULA ANEXA ESTENSION TENEGA | 0 | 111 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/tachira/uribante/cm-pregonero/escuela-bolivariana-ana-ysabel-contreras-de-belandria-aula-anexa-estension-tenega |
| 180902004 | no | TÁCHIRA | URIBANTE | CARDENAS | ESCUELA BASICA BOLIVARIANA CONCENTRADA N° 11 NER 412 | 0 | 57 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/tachira/uribante/cardenas/escuela-basica-bolivariana-concentrada-n-11-ner-412 |
| 181801012 | no | TÁCHIRA | ANDRES BELLO | CM. CORDERO | ESCUELA BASICA ESTADAL UNITARIA BOLIVARIANA 165 NER 533 EL GUAMAL | 1 | 46 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/tachira/andres-bello/cm-cordero/escuela-basica-estadal-unitaria-bolivariana-165-ner-533-el-guamal |
| 191203009 | no | TRUJILLO | PAMPAN | LA PAZ | ALDEA BOLIVARIANA - LA PAZ | 2 | 1334 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/trujillo/pampan/la-paz/aldea-bolivariana-la-paz |
| 200303010 | no | YARACUY | NIRGUA | TEMERLA | CASA COMUNAL LA PICA FRIA | 1 | 116 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/yaracuy/nirgua/temerla/casa-comunal-la-pica-fria |
| 210305026 | no | ZULIA | COLON | SANTA BARBARA | CDA ALI PRIMERA | 0 | 228 | 2024v2 | https://regionales.macedoniadelnorte.com/zulia/colon/santa-barbara/cda-ali-primera |
| 211104002 | no | ZULIA | LAGUNILLAS | CAMPO LARA | ESCUELA  SOCIAL DE AVANZADA CAMPO LARA | 2 | 1212 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/zulia/lagunillas/campo-lara/escuela-social-de-avanzada-campo-lara |
| 211502004 | no | ZULIA | VALMORE RODRIGUEZ | LA VICTORIA | UNIDAD EDUCATIVA NACIONAL RAFAEL URDANETA | 4 | 3306 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/zulia/valmore-rodriguez/la-victoria/unidad-educativa-nacional-rafael-urdaneta |
| 211803033 | no | ZULIA | SAN FRANCISCO | SAN FRANCISCO | ESCUELA BASICA NACIONAL GRAN MARISCAL DE AYACUCHO | 5 | 4207 | 2024v2, 2024 | https://regionales.macedoniadelnorte.com/zulia/san-francisco/san-francisco/escuela-basica-nacional-gran-mariscal-de-ayacucho |
| 220101023 | no | AMAZONAS | ATURES | FERNANDO GIRON TOVAR | CENTRO EDUCATIVO INTEGRAL BOLIVARIANO RIO VENTUARI | 1 | 489 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/amazonas/atures/fernando-giron-tovar/centro-educativo-integral-bolivariano-rio-ventuari |
| 220402001 | no | AMAZONAS | RIO NEGRO | SOLANO | ESCUELA BASICA ROMULO GALLEGOS | 0 | 258 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/amazonas/rio-negro/solano/escuela-basica-romulo-gallegos |
| 220404002 | no | AMAZONAS | RIO NEGRO | COCUY | UNIDAD EDUCATIVA EL COCUY | 0 | 184 | 2024v2 | https://regionales.macedoniadelnorte.com/amazonas/rio-negro/cocuy/unidad-educativa-el-cocuy |
| 220602004 | no | AMAZONAS | MANAPIARE | ALTO VENTUARI | CENTRO MOVIL CAÑO IGUANA | 0 | 107 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/amazonas/manapiare/alto-ventuari/centro-movil-cano-iguana |
| 220704002 | no | AMAZONAS | ALTO ORINOCO | MAVACA | UNIDAD EDUCATIVA YANOMAMI I | 0 | 513 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/amazonas/alto-orinoco/mavaca/unidad-educativa-yanomami-i |
| 230303004 | no | DELTA AMACURO | ANTONIO DIAZ | MANUEL RENAUD | E.B.NTRA. SRA DE LA CONSOLATA - ARAGUABISI | 0 | 467 | 2024v2, 2018, 2015 | https://regionales.macedoniadelnorte.com/delta-amacuro/antonio-diaz/manuel-renaud/ebntra-sra-de-la-consolata-araguabisi |
| 240104003 | no | LA GUAIRA | VARGAS | CATIA LA MAR | UNIDAD EDUCATIVA INSTITUTO DE CIENCIAS DEL MAR | 2 | 1134 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/la-guaira/vargas/catia-la-mar/unidad-educativa-instituto-de-ciencias-del-mar |
| 240111026 | no | LA GUAIRA | VARGAS | CARLOS SOUBLETTE | DESARROLLO URBANISTICO MARE ABAJO | 2 | 1162 | 2024v2, 2024, 2018, 2015 | https://regionales.macedoniadelnorte.com/la-guaira/vargas/carlos-soublette/desarrollo-urbanistico-mare-abajo |

## Archivos generados

- `tm_2025_missing_centers_candidates.csv`
- `backend\tm_2025_macedonia_estandar_candidate_completed.csv`
- `docs\tm\TM_2025_MISSING_CENTERS.md`
