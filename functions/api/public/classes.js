export async function onRequest(context) {
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
