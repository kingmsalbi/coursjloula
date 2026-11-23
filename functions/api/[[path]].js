import { onRequest as studentsHandler } from './public/students.js';

export async function onRequest(context) {
    const url = new URL(context.request.url);

    if (url.pathname === '/api/public/classes') {
        const classes = [
            { id: 1, name: "1s1", level: "1ère Année" },
            { id: 2, name: "1s2", level: "1ère Année" },
            { id: 3, name: "1s3", level: "1ère Année" },
            { id: 4, name: "2 IT", level: "2ème Année" },
            { id: 5, name: "2 ECO", level: "2ème Année" },
            { id: 6, name: "2 Lettre", level: "2ème Année" },
            { id: 7, name: "2 science", level: "2ème Année" },
            { id: 8, name: "3eco", level: "3ème Année" },
            { id: 9, name: "4 science", level: "4ème Année" },
            { id: 10, name: "4eco", level: "4ème Année" }
        ];
        return new Response(JSON.stringify({ classes }), {
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=60'
            }
        });
    }

    if (url.pathname === '/api/public/students') {
        try {
            return await studentsHandler(context);
        } catch (e) {}
    }

    const targetUrl = `https://coursjloula.onrender.com${url.pathname}${url.search}`;
    
    // Copy headers and set host
    const headers = new Headers(context.request.headers);
    headers.delete('host');
    headers.set('X-Forwarded-Host', url.host);
    headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

    const init = {
        method: context.request.method,
        headers: headers,
        redirect: 'follow'
    };

    // Body is only allowed for non-GET / non-HEAD requests
    if (context.request.method !== 'GET' && context.request.method !== 'HEAD') {
        try {
            init.body = await context.request.clone().arrayBuffer();
        } catch (e) {
            init.body = context.request.body;
        }
    }

    try {
        const response = await fetch(targetUrl, init);
        return response;
    } catch (err) {
        return new Response(JSON.stringify({ 
            error: 'Le serveur est en cours de réveil ou temporairement indisponible. Veuillez patienter 10 secondes et réessayer.', 
            details: String(err) 
        }), {
            status: 502,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}
