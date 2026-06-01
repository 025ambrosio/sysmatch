import {
  ShoppingBag,
  Package,
  Music2,
  Sparkles,
  Store,
  ShoppingCart,
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
  { slug: "magalu", name: "Magalu", color: "bg-blue-600", icon: Store },
  { slug: "vtex", name: "VTEX", color: "bg-rose-600", icon: ShoppingCart },
];

export function findMarketplace(slug: string): Marketplace | undefined {
  return MARKETPLACES.find((m) => m.slug === slug);
}
