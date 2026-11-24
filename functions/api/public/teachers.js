// Cloudflare Pages Function - /api/public/teachers
export async function onRequest(context) {
  return handleRequest(context);
}

export async function onRequestGet(context) {
  return handleRequest(context);
}

async function handleRequest(context) {
  const teachers = [
    { id: 1, username: "msalbi", full_name: "Professeur Msalbi", email: "msalbi.prof@education.tn", role: "teacher" },
    { id: 88, username: "jamila.rahmeni", full_name: "Jamila Rahmeni", email: "jamila.rahmeni@education.tn", role: "teacher" }
  ];

  return new Response(JSON.stringify({ teachers }), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Access-Control-Allow-Origin': '*'
    }
  });
}
