Our MVC
=======

Model
-----
A model 

Example: ArtistSelector
=======================

App
---
- app model gets created
- app controller gets created, with the app model
- an app view gets created and added to the controller

ArtistSelector
--------------
- app controller gets asked for an MVsC triad for ArtistSelector
- ArtistSelector controller gets asked to populate
- AS controller asks model to get its data using .get()
- model looks up data and responds with rows of data
- AS controller receives list of rows and calls self.addItem
- AS subclass implementation of addItem calls add_row on all views

Artist
------
- when user right-clicks and asks for Info on an artist,
  with a list of selected items (ArtistModel)
- ArtistSelectorController asks root to get a triad for Artist
- then asks new Artist controller to populate,
- 

Code Layout
-----------
- model in dadcouch.model.daddb.ArtistSelectorModel
- controller in dad.controller.selector.ArtistSelectorController
- view in dadgtk.views.views.ArtistSelectorView


Selector
========

The selector combines an ArtistSelector, an AlbumSelector and a TrackSelector.

Choosing artists in the ArtistSelector view filters the AlbumSelector view and
the Track view by passing a list of mid's for the selected artists.

The track selector model contains, for each track:
 - 

Selecting an artist in the artist view should filter the track view to
only the tracks performed by that artist.

The artist view is built from the track list.  For each track, a list of
artists is emitted as the most reliable mid:
- if there are artists on the document, the database id of them; stop
- if there are resolved fingerprints on the document, the musicbrainz artist id mid for each fragment that has one; stop
- if there is metadata, the musicbrainz id mid, then the artist name mid
- otherwise, there is no artist info


To this end:
 - 
