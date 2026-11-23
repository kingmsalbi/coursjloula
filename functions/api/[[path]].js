export async function onRequest(context) {
    const url = new URL(context.request.url);
    const targetUrl = `https://coursjloula.onrender.com${url.pathname}${url.search}`;
    
    // Copy headers and set host
    const headers = new Headers(context.request.headers);
    headers.set('X-Forwarded-Host', url.host);
    headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

    const init = {
        method: context.request.method,
        headers: headers,
        redirect: 'follow'
    };

    // Body is only allowed for non-GET / non-HEAD requests
    if (context.request.method !== 'GET' && context.request.method !== 'HEAD') {
        init.body = context.request.body;
    }

    try {
        const response = await fetch(targetUrl, init);
        return response;
    } catch (err) {
        return new Response(JSON.stringify({ error: 'Erreur de connexion au serveur backend', details: String(err) }), {
            status: 502,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}
