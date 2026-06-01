import { Link, useRouterState } from "@tanstack/react-router";
import { FileText, LayoutDashboard, PackageCheck, Settings } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { MARKETPLACES } from "@/lib/marketplaces";

export function AppSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const isExact = (url: string) => pathname === url;
  const isPrefix = (url: string) => pathname === url || pathname.startsWith(url + "/");

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <PackageCheck className="h-5 w-5" />
          </div>
          <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold text-sidebar-foreground">Conciliador</span>
            <span className="text-[11px] text-sidebar-foreground/70">NF x Etiquetas</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Geral</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={isExact("/")}>
                  <Link to="/" className="flex items-center gap-2">
                    <LayoutDashboard className="h-4 w-4" />
                    <span>Dashboard geral</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={isExact("/zpl-converter")}>
                  <Link to="/zpl-converter" className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    <span>Conversor ZPL</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Marketplaces</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {MARKETPLACES.map((m) => {
                const url = `/marketplace/${m.slug}`;
                const Icon = m.icon;
                return (
                  <SidebarMenuItem key={m.slug}>
                    <SidebarMenuButton asChild isActive={isPrefix(url)}>
                      <Link to={url} className="flex items-center gap-2">
                        <span className={`flex h-5 w-5 items-center justify-center rounded ${m.color} text-white`}>
                          <Icon className="h-3 w-3" />
                        </span>
                        <span>{m.name}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Sistema</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={isExact("/configuracoes")}>
                  <Link to="/configuracoes" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    <span>Configurações</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
