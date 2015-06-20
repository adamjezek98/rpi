<?php
date_default_timezone_set(date_default_timezone_get());
$data["title"] = "titulek";
$data["head"] = "nadpis";
$data["article"] = "clanek";
$data["last_date"] = date( 'G:i:s d/m/Y', time());
$temps["cpu"] = 10;
$temps["power_source"] = 10;
$temps["outside"] = 10;
$temps["room"] = 10;
extract($data);
require("templates/home.phtml");
?>