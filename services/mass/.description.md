The Metadata Artifact Search Service uses search parameters to look for metadata.

### Quick Overview of API
There are two available API endpoints that follow the RPC pattern (not REST):
One endpoint ("GET /rpc/search-options") will return an overview of all metadata classes that can be targeted
by a search. The actual search endpoint ("POST /rpc/search") can be used to search for these target classes using keywords. Hits will be reported in the context of the selected target class.
This means that target classes will be reported that match the specified search query,
however, the target class might contain embedded other classes and the match might
occur in these embedded classes, too.

Along with the hits, facet options are reported that can be used to filter down the hits by
performing the same search query again but with specific facet selections being set.

The search endpoint supports pagination to deal with large hit lists. Facet options can
help avoid having to rely on this feature by filtering down the number of hits to a single page.

For more information see the OpenAPI spec linked below.
