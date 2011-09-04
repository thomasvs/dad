Artist
------
- DAD knows about an artist:
  - because it is referenced in tracks
  - because there is an artist object in the database

- Artists can be looked up by:
  - their unique database id (if the artist object exists)
  - their musicbrainz id (which should distinguish them from other artists
    with the same name)
  - their name (which is not guaranteed unique; two different artists can
    have the same name)

- The mid serves to uniquely reference artists regardless of whether they
  exist as a separate object in the database.

- Artist objects get created in the database:
  - when an artist gets scored for the first time
  - when disambiguating artists ?

- tracks reference artists:
  - because of the metadata which possibly includes artist name and mbid
  - because of acoustic fingerprinting data which relates it to an mbid and name
  - because of being explicitly linked to an artist object, including name, and possibly including mb id

- Code should assume artists with the same name are the same artist, unless
  something explicitly disambiguates them:
  - the mbid
  - the artist id

- Two artists are considered different if:
  - they have different database id's
  - they have different mb id's

- Different artists should have different display names so the difference
  can be seen
