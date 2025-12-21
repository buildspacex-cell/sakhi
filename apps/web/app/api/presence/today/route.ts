import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const personId = searchParams.get("person_id");
  if (!personId) {
    return NextResponse.json({ error: "person_id required" }, { status: 400 });
  }

  const today = new Date().toISOString().slice(0, 10);
  const { data, error } = await supabase
    .from("presence_state")
    .select("*")
    .eq("person_id", personId)
    .eq("date", today)
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
  return NextResponse.json(data);
}
