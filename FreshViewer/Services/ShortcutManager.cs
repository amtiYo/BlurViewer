using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia.Input;

namespace FreshViewer.Services;

/// <summary>
/// Управляет профилями и ремаппингом горячих клавиш. Позволяет импорт/экспорт JSON.
/// </summary>
public sealed class ShortcutManager
{
    private readonly Dictionary<ShortcutAction, List<KeyCombo>> _actionToCombos = new();

    public ShortcutManager()
    {
        ResetToProfile("Стандартный");
    }

    public IReadOnlyList<string> Profiles { get; } = new[] { "Стандартный", "Photoshop", "Lightroom" };

    public void ResetToProfile(string profileName)
    {
        _actionToCombos.Clear();

        switch (profileName)
        {
            case "Photoshop":
                ApplyStandardBase();
                // Дополнительно: повороты как в Lightroom/PS: Ctrl+[ и Ctrl+]
                Set(ShortcutAction.RotateCounterClockwise, new KeyCombo(Key.Oem4, KeyModifiers.Control));
                Set(ShortcutAction.RotateClockwise, new KeyCombo(Key.Oem6, KeyModifiers.Control));
                break;
            case "Стандартный":
            default:
                ApplyStandardBase();
                break;
        }
    }

    private void ApplyStandardBase()
    {
        // Навигация
        Set(ShortcutAction.Previous, new KeyCombo(Key.Left), new KeyCombo(Key.A));
        Set(ShortcutAction.Next, new KeyCombo(Key.Right), new KeyCombo(Key.D));

        // Просмотр
        Set(ShortcutAction.Fit, new KeyCombo(Key.Space), new KeyCombo(Key.F));
        Set(ShortcutAction.ZoomIn, new KeyCombo(Key.OemPlus), new KeyCombo(Key.Add));
        Set(ShortcutAction.ZoomOut, new KeyCombo(Key.OemMinus), new KeyCombo(Key.Subtract));
        Set(ShortcutAction.RotateClockwise, new KeyCombo(Key.R));
        Set(ShortcutAction.RotateCounterClockwise, new KeyCombo(Key.L));

        // Окно/интерфейс
        Set(ShortcutAction.Fullscreen, new KeyCombo(Key.F11));
        Set(ShortcutAction.ToggleUi, new KeyCombo(Key.Q));
        Set(ShortcutAction.ToggleInfo, new KeyCombo(Key.I));
        Set(ShortcutAction.ToggleSettings, new KeyCombo(Key.P));

        // Файл/буфер
        Set(ShortcutAction.OpenFile, new KeyCombo(Key.O, KeyModifiers.Control));
        Set(ShortcutAction.CopyFrame, new KeyCombo(Key.C, KeyModifiers.Control));
    }

    private void Set(ShortcutAction action, params KeyCombo[] combos)
    {
        _actionToCombos[action] = combos.ToList();
    }

    public bool TryMatch(KeyEventArgs e, out ShortcutAction action)
    {
        foreach (var pair in _actionToCombos)
        {
            foreach (var combo in pair.Value)
            {
                if (combo.Matches(e))
                {
                    action = pair.Key;
                    return true;
                }
            }
        }

        action = default;
        return false;
    }

    public async Task<string> ExportToJsonAsync()
    {
        var export = _actionToCombos.ToDictionary(
            p => p.Key.ToString(),
            p => p.Value.Select(KeyComboFormat.Format).ToArray());

        var options = new JsonSerializerOptions { WriteIndented = true };
        return await Task.Run(() => JsonSerializer.Serialize(export, options));
    }

    public void ImportFromJson(string json)
    {
        var doc = JsonSerializer.Deserialize<Dictionary<string, string[]>>(json);
        if (doc is null)
        {
            return;
        }

        _actionToCombos.Clear();
        foreach (var (actionName, combos) in doc)
        {
            if (!Enum.TryParse<ShortcutAction>(actionName, ignoreCase: true, out var action))
            {
                continue;
            }

            var parsed = combos.Select(KeyComboFormat.Parse).Where(static c => c is not null).Cast<KeyCombo>().ToList();
            if (parsed.Count > 0)
            {
                _actionToCombos[action] = parsed;
            }
        }
    }
}

public enum ShortcutAction
{
    Previous,
    Next,
    Fit,
    ZoomIn,
    ZoomOut,
    RotateClockwise,
    RotateCounterClockwise,
    Fullscreen,
    ToggleUi,
    ToggleInfo,
    ToggleSettings,
    OpenFile,
    CopyFrame
}

public readonly struct KeyCombo
{
    public KeyCombo(Key key, KeyModifiers modifiers = KeyModifiers.None)
    {
        Key = key;
        Modifiers = modifiers;
    }

    public Key Key { get; }
    public KeyModifiers Modifiers { get; }

    public bool Matches(KeyEventArgs e)
    {
        if (e.Key != Key)
        {
            return false;
        }

        // Нормализуем модификаторы (NumLock/Scroll не влияют)
        var mods = e.KeyModifiers & (KeyModifiers.Control | KeyModifiers.Shift | KeyModifiers.Alt | KeyModifiers.Meta);
        return mods == Modifiers;
    }
}

internal static class KeyComboFormat
{
    public static string Format(KeyCombo combo)
    {
        var parts = new List<string>();
        if (combo.Modifiers.HasFlag(KeyModifiers.Control)) parts.Add("Ctrl");
        if (combo.Modifiers.HasFlag(KeyModifiers.Shift)) parts.Add("Shift");
        if (combo.Modifiers.HasFlag(KeyModifiers.Alt)) parts.Add("Alt");
        if (combo.Modifiers.HasFlag(KeyModifiers.Meta)) parts.Add("Meta");

        parts.Add(KeyToString(combo.Key));
        return string.Join('+', parts);
    }

    public static KeyCombo? Parse(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return null;
        }

        var parts = text.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var mods = KeyModifiers.None;
        Key? key = null;

        foreach (var p in parts)
        {
            switch (p.ToLowerInvariant())
            {
                case "ctrl":
                case "control":
                    mods |= KeyModifiers.Control; break;
                case "shift":
                    mods |= KeyModifiers.Shift; break;
                case "alt":
                    mods |= KeyModifiers.Alt; break;
                case "meta":
                case "win":
                    mods |= KeyModifiers.Meta; break;
                default:
                    key = StringToKey(p);
                    break;
            }
        }

        if (key is null)
        {
            return null;
        }

        return new KeyCombo(key.Value, mods);
    }

    private static string KeyToString(Key key)
    {
        return key switch
        {
            Key.OemPlus => "+",
            Key.Add => "+",
            Key.OemMinus => "-",
            Key.Subtract => "-",
            Key.Oem4 => "[",
            Key.Oem6 => "]",
            _ => key.ToString()
        };
    }

    private static Key? StringToKey(string s)
    {
        return s switch
        {
            "+" or "plus" => Key.OemPlus,
            "-" or "minus" => Key.OemMinus,
            "[" => Key.Oem4,
            "]" => Key.Oem6,
            _ => Enum.TryParse<Key>(s, true, out var k) ? k : null
        };
    }
}


