using System;
using System.IO;
using Avalonia;

namespace FreshViewer;

internal static class Program
{
    private static readonly string StartupLogPath = Path.Combine(AppContext.BaseDirectory, "startup.log");

    [STAThread]
    public static void Main(string[] args)
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("FreshViewer is now available on Windows only.");
        }

        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp()
        => AppBuilder.Configure<App>()
            .UseWin32()
            .UseSkia()
            .WithInterFont()
            .LogToTrace();
}
