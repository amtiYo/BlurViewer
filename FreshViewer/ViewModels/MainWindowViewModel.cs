using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using FreshViewer.Models;

namespace FreshViewer.ViewModels;

public sealed class MainWindowViewModel : INotifyPropertyChanged
{
    private string? _fileName;
    private string? _resolutionText;
    private string _statusText = "Откройте изображение";
    private bool _isMetadataVisible;
    private bool _isUiVisible = true;
    private bool _isMetadataCardVisible;
    private bool _isInfoPanelVisible;
    private IReadOnlyList<MetadataSectionViewModel>? _metadataSections;
    private IReadOnlyList<MetadataItemViewModel>? _summaryItems;
    private bool _hasSummaryItems;
    private bool _hasMetadataDetails;
    private bool _showMetadataPlaceholder = true;
    private bool _isErrorVisible;
    private string? _errorTitle;
    private string? _errorDescription;
    private bool _isSettingsPanelVisible;
    private string? _galleryPositionText;
    private string _selectedTheme = "Liquid Dawn";
    private string _selectedLanguage = "Русский";
    private string _selectedShortcutProfile = "Стандартный";
    private bool _enableLiquidGlass = true;
    private bool _enableAmbientAnimations = true;

    public event PropertyChangedEventHandler? PropertyChanged;

    public string? FileName
    {
        get => _fileName;
        set => SetField(ref _fileName, value);
    }

    public string? ResolutionText
    {
        get => _resolutionText;
        set => SetField(ref _resolutionText, value);
    }

    public string StatusText
    {
        get => _statusText;
        set => SetField(ref _statusText, value);
    }

    public bool IsMetadataVisible
    {
        get => _isMetadataVisible;
        set
        {
            if (SetField(ref _isMetadataVisible, value))
            {
                UpdateMetadataCardVisibility();
            }
        }
    }

    public bool IsUiVisible
    {
        get => _isUiVisible;
        set
        {
            if (SetField(ref _isUiVisible, value))
            {
                UpdateMetadataCardVisibility();

                if (!value)
                {
                    if (IsInfoPanelVisible)
                    {
                        IsInfoPanelVisible = false;
                    }

                    if (IsSettingsPanelVisible)
                    {
                        IsSettingsPanelVisible = false;
                    }
                }
            }
        }
    }

    public bool IsMetadataCardVisible
    {
        get => _isMetadataCardVisible;
        private set => SetField(ref _isMetadataCardVisible, value);
    }

    public bool IsInfoPanelVisible
    {
        get => _isInfoPanelVisible;
        set
        {
            if (SetField(ref _isInfoPanelVisible, value) && value)
            {
                if (IsSettingsPanelVisible)
                {
                    IsSettingsPanelVisible = false;
                }
            }
        }
    }

    public bool IsSettingsPanelVisible
    {
        get => _isSettingsPanelVisible;
        set
        {
            if (SetField(ref _isSettingsPanelVisible, value) && value)
            {
                if (IsInfoPanelVisible)
                {
                    IsInfoPanelVisible = false;
                }
            }
        }
    }

    public IReadOnlyList<MetadataSectionViewModel>? MetadataSections
    {
        get => _metadataSections;
        set => SetField(ref _metadataSections, value);
    }

    public IReadOnlyList<MetadataItemViewModel>? SummaryItems
    {
        get => _summaryItems;
        private set
        {
            if (SetField(ref _summaryItems, value))
            {
                HasSummaryItems = value is { Count: > 0 };
            }
        }
    }

    public bool HasSummaryItems
    {
        get => _hasSummaryItems;
        private set => SetField(ref _hasSummaryItems, value);
    }

    public bool HasMetadataDetails
    {
        get => _hasMetadataDetails;
        set => SetField(ref _hasMetadataDetails, value);
    }

    public bool ShowMetadataPlaceholder
    {
        get => _showMetadataPlaceholder;
        set => SetField(ref _showMetadataPlaceholder, value);
    }

    public string? GalleryPositionText
    {
        get => _galleryPositionText;
        set => SetField(ref _galleryPositionText, value);
    }

    public bool IsErrorVisible
    {
        get => _isErrorVisible;
        set => SetField(ref _isErrorVisible, value);
    }

    public string? ErrorTitle
    {
        get => _errorTitle;
        set => SetField(ref _errorTitle, value);
    }

    public string? ErrorDescription
    {
        get => _errorDescription;
        set => SetField(ref _errorDescription, value);
    }

    public IReadOnlyList<string> ThemeOptions { get; } = new[]
    {
        "Liquid Dawn",
        "Midnight Flow",
        "Frosted Steel"
    };

    public IReadOnlyList<string> LanguageOptions { get; } = new[]
    {
        "Русский",
        "English",
        "Українська",
        "Deutsch"
    };

    public IReadOnlyList<string> ShortcutProfiles { get; } = new[]
    {
        "Стандартный",
        "Photoshop",
        "Lightroom"
    };

    public string SelectedTheme
    {
        get => _selectedTheme;
        set => SetField(ref _selectedTheme, value);
    }

    public string SelectedLanguage
    {
        get => _selectedLanguage;
        set => SetField(ref _selectedLanguage, value);
    }

    public string SelectedShortcutProfile
    {
        get => _selectedShortcutProfile;
        set => SetField(ref _selectedShortcutProfile, value);
    }

    public bool EnableLiquidGlass
    {
        get => _enableLiquidGlass;
        set => SetField(ref _enableLiquidGlass, value);
    }

    public bool EnableAmbientAnimations
    {
        get => _enableAmbientAnimations;
        set => SetField(ref _enableAmbientAnimations, value);
    }

    public void ApplyMetadata(string? fileName, string? resolution, string statusMessage, ImageMetadata? metadata)
    {
        FileName = fileName;
        ResolutionText = resolution;
        StatusText = statusMessage;
        IsMetadataVisible = !string.IsNullOrWhiteSpace(fileName);
        MetadataSections = MetadataViewModelFactory.Create(metadata);
        HasMetadataDetails = MetadataSections is { Count: > 0 };
        SummaryItems = MetadataSections?.FirstOrDefault()?.Items?.Take(6).ToList();
        ShowMetadataPlaceholder = !HasSummaryItems;
        GalleryPositionText = null;
        IsErrorVisible = false;
        ErrorTitle = null;
        ErrorDescription = null;
        UpdateMetadataCardVisibility();
    }

    public void ResetMetadata()
    {
        FileName = null;
        ResolutionText = null;
        MetadataSections = null;
        SummaryItems = null;
        HasMetadataDetails = false;
        ShowMetadataPlaceholder = true;
        IsMetadataVisible = false;
        GalleryPositionText = null;
        UpdateMetadataCardVisibility();
    }

    public void ShowError(string title, string description)
    {
        ErrorTitle = title;
        ErrorDescription = description;
        IsErrorVisible = true;
    }

    public void HideError()
    {
        IsErrorVisible = false;
        ErrorTitle = null;
        ErrorDescription = null;
    }

    private bool SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (!Equals(field, value))
        {
            field = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
            return true;
        }

        return false;
    }

    private void UpdateMetadataCardVisibility()
    {
        IsMetadataCardVisible = _isUiVisible && _isMetadataVisible;
    }
}
