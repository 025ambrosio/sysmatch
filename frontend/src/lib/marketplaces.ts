import {
  ShoppingBag,
  Package,
  Music2,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

export interface Marketplace {
  slug: string;
  name: string;
  color: string; // tailwind class for accent bg
  icon: LucideIcon;
}

export const MARKETPLACES: Marketplace[] = [
  { slug: "shopee", name: "Shopee", color: "bg-orange-500", icon: ShoppingBag },
  { slug: "amazon", name: "Amazon", color: "bg-amber-600", icon: Package },
  { slug: "tiktok_shop", name: "TikTok Shop", color: "bg-zinc-900", icon: Music2 },
  { slug: "beleza_na_web", name: "Beleza na Web", color: "bg-pink-500", icon: Sparkles },
];

export function findMarketplace(slug: string): Marketplace | undefined {
  return MARKETPLACES.find((m) => m.slug === slug);
}
