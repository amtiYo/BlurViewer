using System;
using System.Globalization;
using Avalonia.Data.Converters;
using Avalonia.Data;

namespace FreshViewer.Converters;

public sealed class BooleanToValueConverter : IValueConverter
{
    public object? TrueValue { get; set; }
    public object? FalseValue { get; set; }

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool flag)
        {
            return flag ? TrueValue : FalseValue;
        }

        return FalseValue;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (TrueValue is not null && Equals(value, TrueValue))
        {
            return true;
        }

        if (FalseValue is not null && Equals(value, FalseValue))
        {
            return false;
        }

        return BindingOperations.DoNothing;
    }
}
