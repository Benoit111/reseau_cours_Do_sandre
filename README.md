Créer un fichier .env à la racine du projet avec ces parametres :


- POSTGRES_USER=
- POSTGRES_PASSWORD=
- POSTGRES_DB=
- POSTGRES_HOST=
- POSTGRES_PORT=
- POSTGRES_SCHEMAS=



Documentation de l’API Stations / Tronçons


1. Récupérer les informations d’une station

Endpoint : GET /stations/{codestation}

Description :
Permet d’obtenir toutes les informations détaillées d’une station spécifique à partir de son code unique.

Retour attendu :

- Identifiant de la station
- Coordonnées géographiques (X, Y)
- Commune et département
- Type et nature de la station
- Code et nom du cours d’eau associé
- Région et autres attributs descriptifs


Usage métier :

Parfait pour obtenir la fiche complète d’une station et l’utiliser dans une analyse ou un affichage cartographique.

2. Trouver les stations amont et aval à partir d’une station

Endpoint : GET /stations/{codestation}/related_stations

Description :
Permet de découvrir les stations situées en amont et en aval d’une station donnée, en suivant le réseau hydrographique.

Retour attendu :

- Liste de stations amont avec leurs coordonnées et distance par rapport au tronçon
- Liste de stations aval avec les mêmes informations


Usage métier :

Utile pour analyser le réseau de suivi hydrologique, planifier des interventions, ou suivre la propagation d’événements sur le réseau (crues, pollution, etc.).

3. Trouver les stations amont et aval à partir d’un tronçon

Endpoint : GET /troncons/{troncon_id}/related_stations

Description :

Identique à la précédente, mais on part d’un tronçon de rivière plutôt que d’une station.

Retour attendu :


- Stations en amont et en aval du tronçon donné


Usage métier :

Permet d’explorer le réseau hydrographique à partir de tronçons connus, utile pour cartographie ou analyse du réseau.

4. Récupérer les tronçons amont et aval à partir d’un tronçon

Endpoint : GET /troncons/{troncon_id}/graph_tronconh

Description :
Permet de récupérer la liste des tronçons situés en amont et en aval d’un tronçon donné.

Retour attendu :


- Tronçons amont et aval au format GeoJSON (prêt à être affiché sur une carte)


Usage métier :

Utile pour visualiser le réseau hydrographique ou pour des calculs sur la connectivité du réseau.

5. Récupérer les tronçons amont et aval à partir d’une station

Endpoint : GET /troncon/{codestation}/graph_tronconh

Description :
Même fonction que le précédent, mais on part d’une station plutôt que d’un tronçon.

Retour attendu :


- Tronçons amont et aval liés à la station, au format GeoJSON

Usage métier :

Permet d’analyser le réseau à partir d’un point de mesure spécifique (station) et d’afficher les tronçons liés sur une carte.

6. Obtenir la route directes entre deux stations

Endpoint : GET stations/between_stations?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}

Endpoint : GET troncon/between_graph_tronconh?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}

Retour attendues :

- Tronçons et statiosn entre deux points (stations)

Usage métier : cela peut permettre la sélection en ligne directe amont/aval 


7. Fonctions internes principales (métier)


- get_troncons_for_station(codestation) : retrouve les tronçons liés à une station.
- resolve_troncon_id_from_idtronconh(idtronconh) : traduit l’identifiant externe d’un tronçon en identifiant interne utilisé pour l’analyse du réseau.
- get_upstream_sections(troncon_id) : récupère tous les tronçons en amont d’un tronçon donné.
- get_downstream_sections(troncon_id) : récupère tous les tronçons en aval d’un tronçon donné.
- get_matching_stations(upstream_df) : relie les tronçons récupérés aux stations présentes dessus, en ajoutant la distance par rapport 
au tronçon.    
- get_matching_section_id(stream_df) : récupère les informations des tronçons, y compris leur géométrie, pour pouvoir les représenter sur une carte.
- get_geodf_between2_stations : Obtenir la route directes entre deux stations


Le fichier stations_troncons_plando.txt  est la source des stations (xy) qui relie le stronçons de la bdcarthage (https://www.data.gouv.fr/datasets/bd-carthage-r)

Les tronçons de la bdcarthage ont été utilisé via Postgres et mis en réseau à l'aide de PGrouting..

tronconhydrograelt_fxx
tronconhydrograelt_fxx_vertices_pgr



**CREATE EXTENSION pgrouting;**

sélectionne les valeurs geom et leur validité (Cela ne doit pas être des mutlilinestring) ainsi que le srid et la dimension de la geométrie

select distinct ST_GeometryType(geom), ST_NDims(geom), ST_SRID(geom),ST_IsValid(geom)
FROM bdcarthage.tronconhydrograelt_fxx;

si multiple, il faut recréer une table en assemblant les geom
Normalement, il ne doit pas avoir ce cas sur les tronçons

ST_LineMerge(geom) AS geom,

La table contient des geometrie 3d, il faut les forcer en 2d

SELECT id, ST_Dimension(geom), ST_Z(geom) AS z_value
FROM bdcarthage.tronconhydrograelt_fxx
WHERE ST_Dimension(geom) = 3
LIMIT 10;

Si oui forcer la geom et updater en 2d

ALTER TABLE bdcarthage.tronconhydrograelt_fxx
  ALTER COLUMN geom TYPE geometry(LINESTRING)
    USING ST_Force2D(geom);

Ajouter un srid si il est absent

ALTER TABLE bdcarthage.tronconhydrograelt_fxx
  ALTER COLUMN geom TYPE geometry(LINESTRING, 2154)
    USING ST_SetSRID(geom,2154);

Verifier la présence de la geom dans geometry_columns


select * from geometry_columns where f_table_name ='tronconhydrograelt_fxx'

Si la table n’est pas présente ajouter là


select populate_geometry_columns()

Verfiier qu il n’y a pas de null ou de doublon dans id si il n’a pas été généré automatiquement


SELECT id, COUNT(*) 
FROM bdcarthage.tronconhydrograelt_fxx
GROUP BY id
HAVING COUNT(*) > 1 OR id IS NULL;

Sinon le genérer automatiquement

WITH cte AS (
  SELECT 
    *, 
    ROW_NUMBER() OVER () AS rn
  FROM bdcarthage.tronconhydrograelt_fxx
)
UPDATE bdcarthage.tronconhydrograelt_fxx
SET id = cte.rn
FROM cte
WHERE bdcarthage.tronconhydrograelt_fxx.gid= cte.gid;

Il faut mettre à jour cette table et créer deux champs source et target.


ALTER TABLE bdcarthage.tronconhydrograelt_fxx ADD COLUMN "source" integer;
ALTER TABLE bdcarthage.tronconhydrograelt_fxx ADD COLUMN "target" integer;

creer la topologie

SELECT pgr_createTopology (‘bdcarthage.tronconhydrograelt_fxx’ ,0.01,‘geom’,‘id’,‘source’,‘target’,‘true’);

Cela crée la table des nœuds :bdtopage.troncon_hydrographique_2022**_vertice_pgr**
et remplit les champs :

    source,
    target’

avec les valeurs correspondante du champ id dans la table tronçon.

Donc nous avons deux tables :

une table des tronçons (des cours d’eau)
une table des sommets (vertices) du graphe (table pgr)
Signification des champs :

id → identifiant unique du sommet (vertex). C’est ce que les fonctions pgRouting utilisent comme référence pour relier les arêtes.

cnt → nombre d’arêtes connectées à ce sommet.
→ Si cnt = 1, c’est une extrémité (source ou puits).
→ Si cnt = 2, c’est un sommet intermédiaire.
→ Si cnt > 2, c’est une intersection (confluence de rivières).

chk → indicateur utilisé par pgRouting pour vérifier la topologie (sert surtout au debug).
→ En général 0, sauf si un problème a été trouvé lors de la création de la topologie.

ein (edge in) → nombre d’arêtes entrant dans ce sommet (utile pour graphes dirigés).

eout (edge out) → nombre d’arêtes sortant de ce sommet.

the_geom → la géométrie du sommet (point). C’est la position XY (et éventuellement Z/M) du nœud extrait des tronçons.

On analyse par la suite


SELECT  pgr_analyzegraph ('bdcarthage.tronconhydrograelt_fxx', 0.01,'geom','id','source','target','true');

Si il existe des erreurs , on peut les résoudre

SELECT  pgr_nodeNetwork ( 'bdcarthage.stations_troncons' ,  0.01 );

Rêquete de distance pour récupérer le code hydro de la stations… le champs verif_cdho est un boléen qui verifie si le code hydro de la stations est identique à celui du troncon.

La requête distance calcul une distance d’une stations sur 3 tronçons car l’information cdtronconh n’est pas toujours indiqué ainsi cela laisse une marge pour obtenir le bon troncons (methode de verification ? )


SELECT 
    p.id AS station_id,
    p.codestation,
    p.inseecom,
    p.coordx,
    p.coordy,
    p.codecourseau,
    p.libellecourseau,
    p.codetronconhydro,
    p.coderegion,
    p.codedepartement,
    p.naturestation,
    p.libellenaturestation,
    p.typeentitehydro,
    t.cdtronconh,
    t.idtronconh,
    t.nomentiteh,
    t.etat,
    t.sens,
    t.largeur,
    t.nature,
    t.navigable,
    t.source,
    t.target,
    t.id AS troncon_id,
    t.gid,
    t.distance,
    CASE
        WHEN codetronconhydro = cdtronconh THEN true
        ELSE false
    END AS verif_cdho
FROM (
        SELECT 
            id,
            codestation,
            inseecom,
            coordx,
            coordy,
            codecourseau,
            libellecourseau,
            codetronconhydro,
            coderegion,
            codedepartement,
            naturestation,
            libellenaturestation,
            typeentitehydro,
            ST_SetSRID(ST_MakePoint(coordx, coordy), 2154) AS geom
        FROM naiades_referentiel_interne.station_full
        WHERE typeentitehydro = '2'  -- cours d'eau
    ) AS p
    CROSS JOIN LATERAL (
        SELECT *,
            st_distance(c.geom, p.geom) AS distance
        FROM bdcarthage.tronconhydrograelt_fxx as c
        ORDER BY (c.geom <-> p.geom)
        LIMIT 3
    ) t

Exemple sur celui de la bd topage

trajet entre les id des deux point suivant source=2795406, target=1397436

create table bdtopage.test as 

WITh test as (
       select * from pgr_dijkstra('SELECT id, source, target, st_length(geom) as cost FROM bdtopage.troncon_hydrographique_2022',2795406,1397436)                     )
SELECT c.id, c.geom, c.topooh, c.statutnomo,c.natureth,
c.positionpa, c.persistanc, c.sensecoule, c.classelarg,
c.cdcourseau,c.projcoordo, c.source, c.target
,test.cost,test.agg_cost from bdtopage.troncon_hydrographique_2022 c, test
WHERE c.id = test.edge;



Usage métier :
Ces fonctions permettent de naviguer dans le réseau hydrographique, de relier stations et tronçons, et de préparer les données pour l’affichage ou l’analyse métier (cartographie, suivi du réseau, étude des distances et connexions).
