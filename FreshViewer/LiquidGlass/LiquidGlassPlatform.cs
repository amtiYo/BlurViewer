using System;

namespace FreshViewer.UI.LiquidGlass
{
    /// <summary>
    /// Определяет, доступен ли полный набор эффектов Liquid Glass.
    /// Теперь FreshViewer поддерживает только Windows, но оставляем переменную
    /// окружения для принудительного включения/отключения эффекта:
    /// FRESHVIEWER_FORCE_LIQUID_GLASS = "0"/"false" или "1"/"true".
    /// </summary>
    internal static class LiquidGlassPlatform
    {
        public static bool SupportsAdvancedEffects { get; } = EvaluateSupport();

        private static bool EvaluateSupport()
        {
            var env = Environment.GetEnvironmentVariable("FRESHVIEWER_FORCE_LIQUID_GLASS");
            if (!string.IsNullOrWhiteSpace(env))
            {
                if (env == "1" || env.Equals("true", StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }

                if (env == "0" || env.Equals("false", StringComparison.OrdinalIgnoreCase))
                {
                    return false;
                }
            }

            if (!OperatingSystem.IsWindows())
            {
                return false;
            }

            return true;
        }
    }
}
