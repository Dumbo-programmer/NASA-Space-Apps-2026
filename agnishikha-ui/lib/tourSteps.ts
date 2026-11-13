import type { TabKey } from "@/components/TabBar";

/** target = value of the data-tour attribute on the element to spotlight. tab = tab that must be open first. */
export interface TourStep { target: string; title: string; body: string; tab?: TabKey }

export const TOUR_STEPS: TourStep[] = [
  { target: "app-title", title: "Welcome to AstraFlame", body: "It predicts how fire behaves in space, and shows where the NASA data we used runs out." },
  { target: "tabs", title: "Real models vs demos", body: "Habitat Map and NASA Models use trained NASA models. The other tabs are illustrative demos." },
  { target: "hab-stats", tab: "habitat", title: "The gap", body: "Our NASA data has 0 space fire tests at habitat pressure. These three numbers show why that matters." },
  { target: "hab-picker", tab: "habitat", title: "Pick an atmosphere", body: "Choose Space Station air, Moon or Mars habitat air, your own mix, or a live sensor chamber." },
  { target: "hab-map", tab: "habitat", title: "Read the map", body: "Blue: flame goes out. Orange: it keeps burning. Faded: far from any NASA test. Black dots: past NASA tests. Letters A to E: best next tests." },
  { target: "hab-answer", tab: "habitat", title: "Your answer", body: "Green means our NASA data has a test close to this. Amber means it is an informed guess." },
  { target: "hab-materials", tab: "habitat", title: "Materials", body: "See which materials can burn at 34% oxygen. This is decision support, not certification." },
  { target: "tab-models", title: "Ask the real models", body: "Open NASA Models to change inputs yourself and see each answer with its 90% range and a warning outside NASA's tested range." },
];
