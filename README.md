# API Stations / Tronçons — Réseau hydrographique

Documentation de l'API permettant de naviguer dans le réseau hydrographique (stations Naïades ↔ tronçons BD Carthage / BD Topage), via PostgreSQL + PostGIS + pgRouting.

## Sommaire

- [Configuration](#configuration)
- [Endpoints API](#endpoints-api)
- [Fonctions internes principales](#fonctions-internes-principales)
- [Préparation des données (PostGIS / pgRouting)](#préparation-des-données-postgis--pgrouting)
- [Requêtes de rattachement station ↔ tronçon](#requête-de-rattachement-station--tronçon)
- [Exemple de trajet (pgr_dijkstra)](#exemple-de-trajet-pgr_dijkstra)

## Configuration

Créer un fichier `.env` à la racine du projet :

```env
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_SCHEMAS=
```

## Endpoints API

### 1. Récupérer les informations d'une station

```
GET /stations/{codestation}
```

**Description** : renvoie toutes les informations détaillées d'une station à partir de son code unique.

**Retour attendu :**
- Identifiant de la station
- Coordonnées géographiques (X, Y)
- Commune et département
- Type et nature de la station
- Code et nom du cours d'eau associé
- Région et autres attributs descriptifs

**Usage métier** : obtenir la fiche complète d'une station pour une analyse ou un affichage cartographique.

---

### 2. Trouver les stations amont et aval à partir d'une station

```
GET /stations/{codestation}/related_stations
```

**Description** : découvre les stations situées en amont et en aval d'une station donnée, en suivant le réseau hydrographique.

**Retour attendu :**
- Liste des stations amont (coordonnées + distance au tronçon)
- Liste des stations aval (coordonnées + distance au tronçon)

**Usage métier** : analyse du réseau de suivi hydrologique, planification d'interventions, suivi de propagation d'événements (crues, pollution, etc.).

---

### 3. Trouver les stations amont et aval à partir d'un tronçon

```
GET /troncons/{troncon_id}/related_stations
```

**Description** : identique au précédent, mais à partir d'un tronçon de rivière plutôt que d'une station.

**Retour attendu :** stations en amont et en aval du tronçon donné.

**Usage métier** : exploration du réseau hydrographique à partir de tronçons connus (cartographie, analyse du réseau).

---

### 4. Récupérer les tronçons amont et aval à partir d'un tronçon

```
GET /troncons/{troncon_id}/graph_tronconh
```

**Description** : renvoie la liste des tronçons situés en amont et en aval d'un tronçon donné.

**Retour attendu :** tronçons amont et aval au format **GeoJSON** (prêt à être affiché sur une carte).

**Usage métier** : visualisation du réseau hydrographique, calculs de connectivité.

---

### 5. Récupérer les tronçons amont et aval à partir d'une station

```
GET /troncon/{codestation}/graph_tronconh
```

**Description** : même fonction que le point précédent, mais à partir d'une station.

**Retour attendu :** tronçons amont et aval liés à la station, au format GeoJSON.

**Usage métier** : analyse du réseau à partir d'un point de mesure (station), affichage cartographique.

---

### 6. Obtenir la route directe entre deux stations

```
GET /stations/between_stations?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}
GET /troncon/between_graph_tronconh?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}
```

**Retour attendu :** tronçons et stations situés entre les deux points (stations).

**Usage métier** : sélection en ligne directe amont/aval.

## Fonctions internes principales (métier)

| Fonction | Rôle |
|---|---|
| `get_troncons_for_station(codestation)` | Retrouve les tronçons liés à une station. |
| `resolve_troncon_id_from_idtronconh(idtronconh)` | Traduit l'identifiant externe d'un tronçon en identifiant interne utilisé pour l'analyse du réseau. |
| `get_upstream_sections(troncon_id)` | Récupère tous les tronçons en amont d'un tronçon donné. |
| `get_downstream_sections(troncon_id)` | Récupère tous les tronçons en aval d'un tronçon donné. |
| `get_matching_stations(upstream_df)` | Relie les tronçons récupérés aux stations présentes dessus, en ajoutant la distance au tronçon. |
| `get_matching_section_id(stream_df)` | Récupère les informations des tronçons, y compris leur géométrie, pour affichage cartographique. |
| `get_geodf_between2_stations` | Obtient la route directe entre deux stations. |

> Le fichier `stations_troncons_plando.txt` est la source des stations (XY) qui relie les tronçons de la [BD Carthage](https://www.data.gouv.fr/datasets/bd-carthage-r).
>
> Les tronçons de la BD Carthage ont été mis en réseau via **PostgreSQL** à l'aide de **pgRouting** (tables `tronconhydrograelt_fxx` et `tronconhydrograelt_fxx_vertices_pgr`).

## 7. Commande pour démarrer le docker


Le projet est installé sur projet/naiages/naiages_api.

En cas de changement sur les script : 

```shell

#Stopper l'ancien container de prod
docker stop naiage_api
docker rm naiage_api

docker compose down
docker compose build --no-cache
docker compose up -d
docker logs naiades_api_v2 -f
```

## Préparation des données (PostGIS / pgRouting)

### 1. Activer l'extension

```sql
CREATE EXTENSION pgrouting;
```

### 2. Vérifier le type, la dimension, le SRID et la validité des géométries

```sql
SELECT DISTINCT
    ST_GeometryType(geom),
    ST_NDims(geom),
    ST_SRID(geom),
    ST_IsValid(geom)
FROM bdcarthage.tronconhydrograelt_fxx;
```

Si le type est `MULTILINESTRING` (cas normalement absent sur les tronçons), il faut recréer une table en fusionnant les géométries :

```sql
ST_LineMerge(geom) AS geom
```

### 3. Forcer les géométries 3D en 2D

Vérifier la présence de géométries 3D :

```sql
SELECT id, ST_Dimension(geom), ST_Z(geom) AS z_value
FROM bdcarthage.tronconhydrograelt_fxx
WHERE ST_Dimension(geom) = 3
LIMIT 10;
```

Si oui, forcer la géométrie et mettre à jour en 2D :

```sql
ALTER TABLE bdcarthage.tronconhydrograelt_fxx
ALTER COLUMN geom TYPE geometry(LINESTRING)
USING ST_Force2D(geom);
```

### 4. Ajouter un SRID si absent

```sql
ALTER TABLE bdcarthage.tronconhydrograelt_fxx
ALTER COLUMN geom TYPE geometry(LINESTRING, 2154)
USING ST_SetSRID(geom, 2154);
```

### 5. Vérifier la présence de la géométrie dans `geometry_columns`

```sql
SELECT * FROM geometry_columns WHERE f_table_name = 'tronconhydrograelt_fxx';
```

Si la table n'y est pas référencée :

```sql
SELECT populate_geometry_columns();
```

### 6. Vérifier l'absence de doublons ou de valeurs nulles sur `id`

```sql
SELECT id, COUNT(*)
FROM bdcarthage.tronconhydrograelt_fxx
GROUP BY id
HAVING COUNT(*) > 1 OR id IS NULL;
```

Si nécessaire, générer l'identifiant automatiquement :

```sql
WITH cte AS (
    SELECT *, ROW_NUMBER() OVER () AS rn
    FROM bdcarthage.tronconhydrograelt_fxx
)
UPDATE bdcarthage.tronconhydrograelt_fxx
SET id = cte.rn
FROM cte
WHERE bdcarthage.tronconhydrograelt_fxx.gid = cte.gid;
```

### 7. Ajouter les champs `source` et `target`

```sql
ALTER TABLE bdcarthage.tronconhydrograelt_fxx ADD COLUMN "source" integer;
ALTER TABLE bdcarthage.tronconhydrograelt_fxx ADD COLUMN "target" integer;
```

### 8. Créer la topologie

```sql
SELECT pgr_createTopology(
    'bdcarthage.tronconhydrograelt_fxx',
    0.01,
    'geom',
    'id',
    'source',
    'target',
    'true'
);
```

Cela crée la table des nœuds `bdtopage.troncon_hydrographique_2022_vertice_pgr` et remplit les champs `source` / `target` avec les valeurs correspondantes du champ `id` de la table des tronçons.

On obtient ainsi deux tables :
- une table des **tronçons** (cours d'eau) ;
- une table des **sommets** (vertices) du graphe (table `_pgr`).

#### Signification des champs de la table des sommets

| Champ | Signification |
|---|---|
| `id` | Identifiant unique du sommet (vertex), utilisé par pgRouting pour relier les arêtes. |
| `cnt` | Nombre d'arêtes connectées à ce sommet. `1` = extrémité (source ou puits) · `2` = sommet intermédiaire · `>2` = intersection (confluence de rivières). |
| `chk` | Indicateur de vérification de la topologie (debug). En général `0`, sauf problème détecté lors de la création. |
| `ein` (edge in) | Nombre d'arêtes entrant dans ce sommet (graphes dirigés). |
| `eout` (edge out) | Nombre d'arêtes sortant de ce sommet. |
| `the_geom` | Géométrie du sommet (point) — position XY (et éventuellement Z/M) extraite des tronçons. |

### 9. Analyser le graphe

```sql
SELECT pgr_analyzegraph(
    'bdcarthage.tronconhydrograelt_fxx',
    0.01,
    'geom',
    'id',
    'source',
    'target',
    'true'
);
```

En cas d'erreurs, elles peuvent être résolues via :

```sql
SELECT pgr_nodeNetwork('bdcarthage.stations_troncons', 0.01);
```

## Requête de rattachement station ↔ tronçon

Cette requête permet de récupérer le code hydro d'une station. Le champ `verif_cdho` est un booléen qui vérifie si le code hydro de la station est identique à celui du tronçon.

La requête calcule la distance sur les **3 tronçons les plus proches**, car l'information `cdtronconh` n'est pas toujours renseignée : cela laisse une marge pour identifier le bon tronçon (méthode de vérification).

```sql
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
    CASE WHEN codetronconhydro = cdtronconh THEN true ELSE false END AS verif_cdho
FROM (
    SELECT
        id, codestation, inseecom, coordx, coordy, codecourseau, libellecourseau,
        codetronconhydro, coderegion, codedepartement, naturestation,
        libellenaturestation, typeentitehydro,
        ST_SetSRID(ST_MakePoint(coordx, coordy), 2154) AS geom
    FROM naiades_referentiel_interne.station_full
    WHERE typeentitehydro = '2' -- cours d'eau
) AS p
CROSS JOIN LATERAL (
    SELECT *, ST_Distance(c.geom, p.geom) AS distance
    FROM bdcarthage.tronconhydrograelt_fxx AS c
    ORDER BY (c.geom <-> p.geom)
    LIMIT 3
) t;
```

## Exemple de trajet (pgr_dijkstra)

Trajet entre deux points via BD Topage, `source = 2795406`, `target = 1397436` :

```sql
CREATE TABLE bdtopage.test AS
WITH test AS (
    SELECT * FROM pgr_dijkstra(
        'SELECT id, source, target, ST_Length(geom) AS cost FROM bdtopage.troncon_hydrographique_2022',
        2795406,
        1397436
    )
)
SELECT
    c.id, c.geom, c.topooh, c.statutnomo, c.natureth, c.positionpa,
    c.persistanc, c.sensecoule, c.classelarg, c.cdcourseau, c.projcoordo,
    c.source, c.target,
    test.cost, test.agg_cost
FROM bdtopage.troncon_hydrographique_2022 c, test
WHERE c.id = test.edge;
```

---

**Usage métier global** : ces fonctions permettent de naviguer dans le réseau hydrographique, de relier stations et tronçons, et de préparer les données pour l'affichage ou l'analyse métier (cartographie, suivi du réseau, étude des distances et connexions).


![Résultat pgr_dijkstra dans QGIS](dijkstra.png)
