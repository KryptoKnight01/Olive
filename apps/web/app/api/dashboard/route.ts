import { NextRequest, NextResponse } from "next/server";

const API = process.env.OLIVE_API_URL ?? "http://api:8000";

export async function GET(request: NextRequest) {
  const token = request.cookies.get("olive_admin_session")?.value;
  if (!token) return NextResponse.json({ detail: "Sign in required." }, { status: 401 });
  try {
    const upstream = await fetch(`${API}/api/v1/admin/paper-executions?limit=50`, {
      headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
    });
    if (!upstream.ok) return NextResponse.json({ detail: "Session expired." }, { status: upstream.status === 401 ? 401 : 502 });
    return NextResponse.json(await upstream.json());
  } catch {
    return NextResponse.json({ detail: "Olive API is unavailable." }, { status: 502 });
  }
}
