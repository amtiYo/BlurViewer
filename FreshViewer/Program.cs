using System;
using Avalonia;

namespace FreshViewer;

internal static class Program
{
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
