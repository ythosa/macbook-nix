{
  programs.git = {
    enable = true;
    package = null;
    settings = {
      user = {
        name = "ythosa";
        email = "10869361+ythosa@users.noreply.github.com";
      };
      alias = {
        co = "checkout";
        last = "rev-parse --short HEAD";
        br = "branch";
        ci = "commit";
        st = "status";
      };
    };
  };
}
