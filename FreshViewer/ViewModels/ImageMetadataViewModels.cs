using System.Collections.Generic;
using System.Linq;
using FreshViewer.Models;

namespace FreshViewer.ViewModels;

public sealed record MetadataItemViewModel(string Label, string? Value)
{
    public string DisplayValue => string.IsNullOrWhiteSpace(Value) ? "—" : Value;
}

public sealed record MetadataSectionViewModel(string Title, IReadOnlyList<MetadataItemViewModel> Items)
{
    public static MetadataSectionViewModel FromModel(MetadataSection section)
        => new(section.Title, section.Fields.Select(f => new MetadataItemViewModel(f.Label, f.Value)).ToList());
}

public static class MetadataViewModelFactory
{
    public static IReadOnlyList<MetadataSectionViewModel>? Create(ImageMetadata? metadata)
    {
        if (metadata is null)
        {
            return null;
        }

        return metadata.Sections
            .Where(section => section.Fields.Any())
            .Select(MetadataSectionViewModel.FromModel)
            .ToList();
    }
}
