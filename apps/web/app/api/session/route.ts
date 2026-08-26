import { NextRequest, NextResponse } from "next/server";

const API = process.env.OLIVE_API_URL ?? "http://api:8000";
const COOKIE = "olive_admin_session";

export async function POST(request: NextRequest) {
  const { token } = (await request.json()) as { token?: string };
  if (!token || token.length < 16) return NextResponse.json({ detail: "Enter a valid access token." }, { status: 400 });
  try {
    const check = await fetch(`${API}/api/v1/admin/command-center`, {
      headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
    });
    if (!check.ok) return NextResponse.json({ detail: "Access token was not accepted." }, { status: 401 });
    const response = NextResponse.json({ authenticated: true });
    response.cookies.set(COOKIE, token, {
      httpOnly: true, sameSite: "strict", secure: process.env.OLIVE_COOKIE_SECURE === "true",
      path: "/", maxAge: 60 * 60 * 8,
    });
    return response;
  } catch {
    return NextResponse.json({ detail: "Olive API is unavailable." }, { status: 502 });
  }
}

export async function DELETE() {
  const response = NextResponse.json({ authenticated: false });
  response.cookies.set(COOKIE, "", { httpOnly: true, sameSite: "strict", path: "/", maxAge: 0 });
  return response;
}
