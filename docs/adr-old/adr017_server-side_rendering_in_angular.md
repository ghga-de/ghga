# Using Angular Server-Side Rendering

Date: 2024-09-24

## Summary

In the context of **deciding for or against using SSR in our Angular project**

facing **a need for good deveoper experience, good SEO and performanc (Web vitals)**

we decided for **not using SSR**

and neglected **using SSR**

to achieve **a solution that is less costly to develop, maintain and operate**

accepting that **performance could be reduced and in some cases, SEO might suffer**.

## Details

### Status

**accepted**

### Context & Requirements

In an Angular app, two ways of code execution are possible: In the client or in the server. Classically, JavaScript only runs in the browser but newer versions of Angular also allow to run functions on the server. In a client-only setup, the website is a static website, that can be delivered by any web server, that simply returns text files based on routes. Dynamic content is requested from APIs.

When using Server Side Rendering (SSR), a specific web server is built (on the basis of Node.js), that not only returns files but can also execute logic. In this setup, the client doesn't have to rely on external APIs. Instead, the client triggers the execution of functions in the server, that may have better access to the data if they run in the same cloud environment as the APIs and can also handle server side authentication, simplifying certain workflows.

SSR can lead to performance improvements because the client directly receives HTML data that can be added to the DOM instead of having to update the DOM dynamically by transforming a (for example JSON type) API response. Since some search engines crawlers don't execute JavaScript code, SSR can improve SEO performance of the website.

### Decision

Using SSR introduces an additional level of complexity, because developers now have to distinguish for all code where it is being run and running the software is more challenging, because code has to be executed on the server. Whereas scaling the delivery of a purely file-based website is simple with technologies like CDNs, scaling a server side compute infrastructure introduces challenges if the limit of vertical scaling of the server is reached. If, for example, sessions are handled on the server, and we need to run multiple instances due to request load, we have to manage the sessions in such a way that requests are authenticated correctly - independent from the server instance that receives the request - or we have to load balance in such a way to ensure one client always reaches the same server.

If you consider a situation in which the SSR functions call the same APIs as a client-side implementation, SSR also comes at an additional cost because the compute on the client devices causes no cost for the operator of the infrastructure, whereas the additional web servers do.

As discussed in [ADR 16 about the use of semantic web technologies](./adr016_semantic_web_technologies.md), we can mitigate some of the SEO issues by the use of JSON-LD. We also wouldn't change our APIs (in the foreseeable future) to improve the performance of SSR functions, and would therefore likely see *no* performance improvements due to improved data-fetching. Whereas the SSR version could be faster when viewed on a smartphone with slow JavaScript execution, very fast devices (like desktop PCs) could even see a decrease in performance if the web server is slower to execute the SSR functions than the browser on the client would be.

Facing only a small margin of potential gains, the downsides outweigh the advantages. Using SSR would cause additional effort on the operations side, increase the complexity of our software stack and make debugging of issues more complex.

To mitigate more of the potential SEO issues, we can provide a sitemap that lists all of our dataset-urls. While this is independent from the decision to use SSR (or not), a non SSR SPA should take this additional step to ensure crawlers that interpret JavaScript find all the content reliably.

There is also a hybrid of the two systems which is called Server Side Generation or Prerendering. In this paradigm, select pages are pre-rendered at compile time and delivered as static websites at runtime. There are several issues with this idea, however: Changes in the data require rebuilding the website to incorporate new SSG routes, the build becomes more complex to configure and building takes a longer time. As a consequence, the possible advantages for SEO once more don't outweigh the decreased developer experience at this time. This approach also only works for public routes, i.e. for routes that show the same page for every visitor (pre-rendering every user profile for example would generate security risks and lots of data to store). As a consequence, this will not be an option for upcoming features, such as the submitter portal and the data-steward portal.

### Consequences

We will have a better developer experience (easier to debug, no distinction between server side and client side parts) and drastically simpler deployments. On the other hand, we will have to evaluate if SEO performance is up to our needs, i.e. if datasets are indexed in Google.

### Alternatives

We could use SSR right away. We still have the option to enable this feature in the future, however, if a use-case arises, in which it offers real benefits. The same holds for SSG, which we can experiment with in the future.
