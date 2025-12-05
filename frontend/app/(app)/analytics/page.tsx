import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function DashboardCard({ title, value, icon: Icon, trend, className }) {
  return (
    <Card className={cn("overflow-hidden border-border/50 bg-gradient-to-br from-background to-muted/20 transition-all duration-300 hover:shadow-lg hover:border-primary/20", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
            {Icon && <Icon className="h-4 w-4 text-primary" />}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        {trend && (
          <p className="text-xs text-muted-foreground mt-1">
            <span className={trend > 0 ? "text-emerald-500" : "text-rose-500"}>
              {trend > 0 ? "+" : ""}{trend}%
            </span> from last month
          </p>
        )}
      </CardContent>
    </Card>
  );
}