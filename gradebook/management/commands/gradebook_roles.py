from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ...models import Role

#######################################################################


class Command(BaseCommand):
    help = "Manage gradebook roles"

    def add_arguments(self, parser):
        """
        Add arguments to the command.
        """
        parser.add_argument("viewport", nargs="+", help="Specify viewport(s) by slug")
        parser.add_argument(
            "--all",
            action="store_true",
            help="Operate on all roles (default is active only)",
        )
        parser.add_argument(
            "--list-types", action="store_true", help="List the types of roles"
        )
        parser.add_argument(
            "--type", nargs="*", help="Restrict to the given role type(s)"
        )
        parser.add_argument(
            "--dtend",
            help="Update the dtend of the roles to the value given (format: YYYY-MM-DDTHH:MM:SS[+hh:mm])",
        )

    def format_role(self, role):
        """
        Return a string of role values
        """
        r = {}
        for f in [
            "pk",
            "role",
            "person",
            "person_id",
            "viewport",
            "viewport_id",
            "dtstart",
            "dtend",
        ]:
            r[f] = getattr(role, f)
        r["viewport__slug"] = role.viewport.slug
        return "{pk}\t{role}\t{person}\t{viewport__slug}\t{dtstart}\t{dtend}".format_map(
            r
        )

    def handle_datetime_input(self, value):
        dt = parse_datetime(value)
        if dt is None:
            raise RuntimeError("Could not convert value to datetime")
        if settings.USE_TZ and timezone.is_naive(dt):
            default_timezone = timezone.get_default_timezone()
            dt = timezone.make_aware(dt, default_timezone)
        return dt

    # When you are using management commands and wish to provide console output,
    # you should write to self.stdout and self.stderr, instead of printing to
    # stdout and stderr directly. By using these proxies, it becomes much easier
    # to test your custom command. Note also that you don't need to end messages
    # with a newline character, it will be added automatically, unless you
    # specify the ``ending`` parameter to write()
    def handle(self, *args, **options):
        """
        Do the thing!
        """
        qs = Role.objects.all()
        if not options["all"]:
            qs = qs.active()
        qs = qs.filter(viewport__slug__in=options["viewport"])
        if options["type"]:
            qs = qs.filter(role__in=options["type"])

        if options["list_types"]:
            for code, name in Role.CHOICES:
                self.stdout.write("{}\t{}".format(code, name))
        elif options["dtend"]:
            dtend = self.handle_datetime_input(options["dtend"])
            qs.update(dtend=dtend)
        else:
            for item in qs:
                self.stdout.write(self.format_role(item))


#######################################################################
