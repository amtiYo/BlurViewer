using System;
using System.Diagnostics;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Markup.Xaml.Styling;
using Avalonia.Platform;

namespace FreshViewer;

public partial class App : Application
{
    public override void Initialize()
    {
        try
        {
            AvaloniaXamlLoader.Load(this);

            // Загружаем дополнительные стили LiquidGlass только если основная загрузка прошла успешно
            try
            {
                var baseUri = new Uri("avares://FreshViewer/App.axaml");
                var liquidGlassUri = new Uri("avares://FreshViewer/Styles/LiquidGlass.Windows.axaml");
                Resources.MergedDictionaries.Add(new ResourceInclude(baseUri)
                {
                    Source = liquidGlassUri
                });
                Debug.WriteLine("LiquidGlass styles loaded successfully");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Failed to load LiquidGlass styles: {ex.Message}");
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Fatal error during app initialization: {ex}");
            throw;
        }
    }

    public override void OnFrameworkInitializationCompleted()
    {
        try
        {
            if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
            {
                // Создаем главное окно с обработкой ошибок
                Views.MainWindow? window = null;

                try
                {
                    window = new Views.MainWindow();
                    window.InitializeFromArguments(desktop.Args);
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"Error creating main window: {ex}");
                    // Создаем окно без аргументов если с аргументами не получилось
                    window = new Views.MainWindow();
                }

                desktop.MainWindow = window;
                desktop.ShutdownMode = Avalonia.Controls.ShutdownMode.OnMainWindowClose;

                // Подписываемся на события для логирования
                desktop.Exit += (s, e) => Debug.WriteLine($"Application exiting with code {e.ApplicationExitCode}");
            }

            base.OnFrameworkInitializationCompleted();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"Fatal error during framework initialization: {ex}");
            throw;
        }
    }
}
