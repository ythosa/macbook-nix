{
  time.timeZone = "Europe/Moscow";
  networking.applicationFirewall.enable = false;
  system.defaults = {
    NSGlobalDomain = {
      AppleInterfaceStyle = "Dark";
      NSAutomaticCapitalizationEnabled = true;
      NSAutomaticPeriodSubstitutionEnabled = true;
      NSAutomaticWindowAnimationsEnabled = false;
      NSScrollAnimationEnabled = false;
      "com.apple.swipescrolldirection" = true;
      "com.apple.trackpad.forceClick" = true;
      "com.apple.trackpad.scaling" = 2.0;
    };
    dock = {
      autohide = true;
      autohide-time-modifier = 0.0;
      autohide-delay = 0.0;
      expose-animation-duration = 0.1;
      orientation = "bottom";
      magnification = true;
      show-process-indicators = true;
      show-recents = false;
      mru-spaces = false;
      wvous-bl-corner = 14;
      wvous-br-corner = 5;
    };
    finder = {
      FXPreferredViewStyle = "Nlsv";
      ShowExternalHardDrivesOnDesktop = true;
      ShowHardDrivesOnDesktop = false;
      ShowRemovableMediaOnDesktop = true;
    };
    trackpad = {
      Clicking = true;
      TrackpadRightClick = true;
      FirstClickThreshold = 1;
      SecondClickThreshold = 1;
      ForceSuppressed = false;
      TrackpadCornerSecondaryClick = 0;
      TrackpadThreeFingerDrag = false;
      TrackpadThreeFingerTapGesture = 0;
      TrackpadThreeFingerHorizSwipeGesture = 2;
      TrackpadThreeFingerVertSwipeGesture = 2;
      TrackpadFourFingerHorizSwipeGesture = 2;
      TrackpadFourFingerVertSwipeGesture = 2;
      TrackpadMomentumScroll = true;
    };
    CustomUserPreferences = {
      NSGlobalDomain = {
        ApplePressAndHoldEnabled = "0";
        AppleLanguages = [
          "en-RU"
          "ru-RU"
        ];
        AppleLocale = "en_RU";
        "com.apple.mouse.scaling" = 2.0;
        NSScrollViewRubberbanding = false;
        NSWindowResizeTime = ".001";
        QLPanelAnimationDuration = 0.0;
        NSDocumentRevisionsWindowTransformAnimation = false;
        NSToolbarFullScreenAnimationDuration = 0.0;
        NSBrowserColumnAnimationSpeedMultiplier = 0.0;
      };
      "com.apple.dock" = {
        tilesize = 50.0;
        largesize = 60.0;
        springboard-show-duration = 0.0;
        springboard-hide-duration = 0.0;
        springboard-page-duration = 0.0;
      };
      "com.apple.finder" = {
        NewWindowTarget = "PfAF";
        DisableAllAnimations = true;
      };
      "com.apple.AppleMultitouchTrackpad" = {
        DragLock = 0;
        Dragging = 0;
        TrackpadPinch = 1;
        TrackpadRotate = 1;
      };
    };
  };
}
