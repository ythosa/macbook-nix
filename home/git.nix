{
  programs.git = {
    enable = true;
    package = null;
    settings = {
      core.editor = "vim";
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
      url."git@github.com:".insteadOf = "https://github.com/";
      url."ssh://git@".insteadOf = "git://";
    };
  };
}
