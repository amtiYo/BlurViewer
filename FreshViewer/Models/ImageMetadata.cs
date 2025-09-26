using System.Collections.Generic;

namespace FreshViewer.Models;

public sealed class ImageMetadata
{
    public ImageMetadata(IReadOnlyList<MetadataSection> sections, IReadOnlyDictionary<string, string?>? raw = null)
    {
        Sections = sections;
        Raw = raw;
    }

    public IReadOnlyList<MetadataSection> Sections { get; }

    public IReadOnlyDictionary<string, string?>? Raw { get; }
}

public sealed class MetadataSection
{
    public MetadataSection(string title, IReadOnlyList<MetadataField> fields)
    {
        Title = title;
        Fields = fields;
    }

    public string Title { get; }

    public IReadOnlyList<MetadataField> Fields { get; }
}

public sealed class MetadataField
{
    public MetadataField(string label, string? value)
    {
        Label = label;
        Value = value;
    }

    public string Label { get; }

    public string? Value { get; }
}
